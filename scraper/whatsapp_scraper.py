import json
import random
import re
import sys
import time
from datetime import date, datetime, timedelta

from playwright.sync_api import sync_playwright

import config

# nomes de conversa podem trazer caracteres invisíveis (marcas de direção de texto,
# comuns em contatos salvos só como número) que o console do Windows não sabe exibir -
# sem isso, um print() nesses nomes derruba o script inteiro.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# O WhatsApp Web expõe, em cada balão de mensagem, um atributo
# data-pre-plain-text="[HH:MM, DD/MM/AAAA] Remetente: " - é dele que tiramos
# remetente e timestamp. Se a extração vier vazia, o WhatsApp mudou o DOM:
# abra o DevTools (F12) numa conversa, inspecione um balão de mensagem e
# ajuste os seletores abaixo (CHAT_LIST_SELECTOR, MESSAGES_PANE_SELECTOR, etc.).
CHAT_LIST_SELECTOR = 'div[aria-label="Lista de conversas"], div[aria-label="Chat list"]'
CHAT_TITLE_SELECTOR = '[data-testid="cell-frame-title"] span[title]'
MESSAGES_PANE_SELECTOR = (
    'div[data-testid="conversation-panel-messages"], '
    'div[aria-label="Lista de mensagens"], div[aria-label="Message list"]'
)
PRE_PLAIN_TEXT_RE = re.compile(r"^\[(?P<time>\d{1,2}:\d{2}(?::\d{2})?),\s*(?P<date>\d{1,2}/\d{1,2}/\d{4})\]\s*(?P<sender>.*?):\s*$")

# esconde o sinal mais óbvio de automação de navegador (checado por vários sites,
# não se sabe se o WhatsApp usa, mas não custa nada remover)
HIDE_WEBDRIVER_SCRIPT = "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"


def load_progress():
    if config.PROGRESS_FILE.exists():
        return json.loads(config.PROGRESS_FILE.read_text(encoding="utf-8"))
    return {"done": []}


def save_progress(progress):
    config.PROGRESS_FILE.write_text(json.dumps(progress, ensure_ascii=False, indent=2), encoding="utf-8")


def human_delay(bounds):
    time.sleep(random.uniform(*bounds))


def human_click(page, locator):
    # move o mouse em vários passos até o alvo em vez de "teletransportar" o cursor
    # (clique direto é um padrão fácil de reconhecer como automação)
    box = locator.bounding_box()
    if box:
        x = box["x"] + box["width"] / 2 + random.uniform(-4, 4)
        y = box["y"] + box["height"] / 2 + random.uniform(-4, 4)
        page.mouse.move(x, y, steps=random.randint(15, 30))
        human_delay((0.1, 0.3))
    locator.click()


def sanitize_filename(name):
    return re.sub(r'[\\/:*?"<>|]', "_", name).strip()


def parse_export_date(date_str):
    return datetime.strptime(date_str, "%d/%m/%Y").date()


def wait_for_login(page):
    print("Abra o WhatsApp Web e, se aparecer o QR Code, escaneie com o celular (só é preciso na primeira vez).")
    page.wait_for_selector(CHAT_LIST_SELECTOR, timeout=120_000)
    print("Login confirmado.")


def get_page(p):
    """Retorna (page, deve_fechar_no_fim). No modo CDP a página é uma aba do
    seu Chrome real - nunca deve ser fechada por este script."""
    if config.USE_EXISTING_CHROME:
        browser = p.chromium.connect_over_cdp(config.CDP_URL)
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        for existing_page in context.pages:
            if "web.whatsapp.com" in existing_page.url:
                return existing_page, False
        context.add_init_script(HIDE_WEBDRIVER_SCRIPT)
        page = context.new_page()
        page.goto("https://web.whatsapp.com")
        return page, False

    context = p.chromium.launch_persistent_context(user_data_dir=str(config.PROFILE_DIR), headless=False)
    context.add_init_script(HIDE_WEBDRIVER_SCRIPT)
    page = context.pages[0] if context.pages else context.new_page()
    page.goto("https://web.whatsapp.com")
    return page, True


def get_visible_chat_names(page):
    # cada linha da lista tem 2 span[title]: o nome (cell-frame-title) e o preview
    # da última mensagem (last-msg-status) - só o primeiro é o nome da conversa.
    grid = page.locator(CHAT_LIST_SELECTOR).first
    names = []
    seen = set()
    for el in grid.locator(CHAT_TITLE_SELECTOR).all():
        name = el.get_attribute("title")
        if name and name not in seen:
            seen.add(name)
            names.append(name)
    return names


def scroll_sidebar(page):
    grid = page.locator(CHAT_LIST_SELECTOR).first
    grid.hover()
    page.mouse.wheel(0, 1500)
    human_delay(config.DELAY_BETWEEN_SCROLLS)


def open_chat_by_name(page, chat_name):
    safe_name = chat_name.replace('"', '\\"')
    grid = page.locator(CHAT_LIST_SELECTOR).first
    result = grid.locator(f'{CHAT_TITLE_SELECTOR}[title="{safe_name}"]').first
    if result.count() == 0:
        return False
    human_click(page, result)
    human_delay((1.0, 2.0))
    return True


def get_message_bubbles(page):
    pane = page.locator(MESSAGES_PANE_SELECTOR).first
    try:
        pane.locator("div.copyable-text[data-pre-plain-text]").first.wait_for(timeout=8000)
    except Exception:
        return pane, None
    return pane, pane.locator("div.copyable-text[data-pre-plain-text]")


def get_newest_message_date(bubbles):
    if bubbles is None:
        return None
    count = bubbles.count()
    if count == 0:
        return None
    meta = (bubbles.nth(count - 1).get_attribute("data-pre-plain-text") or "").strip()
    match = PRE_PLAIN_TEXT_RE.match(meta)
    if not match:
        return None
    return parse_export_date(match.group("date"))


def scroll_until_cutoff(page, pane, cutoff_date):
    previous_count = -1
    stall = 0
    for _ in range(config.MAX_SCROLL_ATTEMPTS):
        bubbles = pane.locator("div.copyable-text[data-pre-plain-text]")
        current_count = bubbles.count()
        if current_count == previous_count:
            stall += 1
            if stall >= config.SCROLL_STALL_LIMIT:
                break
        else:
            stall = 0
        previous_count = current_count

        if current_count > 0:
            oldest_meta = (bubbles.first.get_attribute("data-pre-plain-text") or "").strip()
            match = PRE_PLAIN_TEXT_RE.match(oldest_meta)
            if match and parse_export_date(match.group("date")) < cutoff_date:
                break

        pane.hover()
        page.mouse.wheel(0, random.randint(-3400, -2200))
        human_delay(config.DELAY_BETWEEN_SCROLLS)

        # de vez em quando, uma pequena correção pra cima - rolagem humana não é
        # uma reta perfeita
        if random.random() < 0.15:
            human_delay((0.3, 0.8))
            page.mouse.wheel(0, random.randint(200, 600))
            human_delay((0.2, 0.5))


def extract_messages(pane, cutoff_date):
    # cada balão de mensagem tem seu próprio data-pre-plain-text (não é preciso "herdar"
    # do anterior). O texto real fica em span[data-testid="selectable-text"] - pegar o
    # innerText do div inteiro incluiria também o preview de mensagem citada (reply).
    elements = pane.locator("div.copyable-text[data-pre-plain-text]").all()
    messages = []
    for el in elements:
        meta = (el.get_attribute("data-pre-plain-text") or "").strip()
        match = PRE_PLAIN_TEXT_RE.match(meta)
        if not match:
            continue

        msg_date = parse_export_date(match.group("date"))
        if msg_date < cutoff_date:
            continue

        sender = match.group("sender").strip()
        dt = f"{match.group('date')}, {match.group('time')}"

        text_spans = el.locator('span[data-testid="selectable-text"]').all()
        text = " ".join(s.inner_text().strip() for s in text_spans).strip()
        if not text:
            text = "<Mídia oculta>"  # sem span de texto = provavelmente foto/áudio/figurinha/documento
        messages.append((dt, sender, text))
    return messages


def save_as_export_txt(chat_name, messages):
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = config.RAW_DIR / f"{sanitize_filename(chat_name)}.txt"
    lines = [f"{ts} - {sender}: {text.replace(chr(10), ' ')}" for ts, sender, text in messages]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main():
    cutoff_date = date.today() - timedelta(days=config.HISTORY_DAYS)
    progress = load_progress()
    done = set(progress["done"])

    print(f"Varrendo conversas na ordem da barra lateral - só mensagens dos últimos {config.HISTORY_DAYS} dias.")

    with sync_playwright() as p:
        page, should_close = get_page(p)
        wait_for_login(page)

        processed = 0
        seen_this_run = set()
        sidebar_stall = 0
        session_start = time.monotonic()
        next_break_at = random.randint(*config.BREAK_EVERY_N_CHATS)

        while processed < config.MAX_CHATS_PER_RUN:
            elapsed_minutes = (time.monotonic() - session_start) / 60
            if elapsed_minutes >= config.MAX_SESSION_MINUTES:
                print(f"Limite de tempo da sessão atingido (~{config.MAX_SESSION_MINUTES} min) - parando por aqui.")
                break

            names = get_visible_chat_names(page)
            new_names = [n for n in names if n not in done and n not in seen_this_run]

            if not new_names:
                scroll_sidebar(page)
                sidebar_stall += 1
                if sidebar_stall >= config.SCROLL_STALL_LIMIT:
                    print("Chegou ao fim da lista de conversas.")
                    break
                continue
            sidebar_stall = 0

            chat_name = new_names[0]
            seen_this_run.add(chat_name)
            processed += 1
            print(f"[{processed}/{config.MAX_CHATS_PER_RUN}] Abrindo '{chat_name}'...")

            if not open_chat_by_name(page, chat_name):
                print("  -> não consegui abrir, pulando.")
                continue

            human_delay(config.READING_DELAY)  # tempo "lendo" antes de rolar pra trás

            pane, bubbles = get_message_bubbles(page)
            newest = get_newest_message_date(bubbles)
            if newest is not None and newest < cutoff_date:
                print(f"  -> sem mensagens nos últimos {config.HISTORY_DAYS} dias, pulando.")
                done.add(chat_name)
                progress["done"] = sorted(done)
                save_progress(progress)
                human_delay(config.DELAY_BETWEEN_CHATS)
                continue

            scroll_until_cutoff(page, pane, cutoff_date)
            messages = extract_messages(pane, cutoff_date)

            if not messages:
                print("  -> nenhuma mensagem no período (ou o WhatsApp Web mudou o DOM - ver comentário no topo do arquivo).")
            else:
                path = save_as_export_txt(chat_name, messages)
                print(f"  -> {len(messages)} mensagens salvas em {path.name}")

            done.add(chat_name)
            progress["done"] = sorted(done)
            save_progress(progress)

            if processed >= next_break_at:
                pausa = random.uniform(*config.BREAK_DURATION)
                print(f"  -> pausa longa de {pausa:.0f}s antes de continuar...")
                time.sleep(pausa)
                next_break_at = processed + random.randint(*config.BREAK_EVERY_N_CHATS)
            else:
                human_delay(config.DELAY_BETWEEN_CHATS)

        if should_close:
            page.context.close()

    print(f"Lote concluído - {processed} conversa(s) processada(s) nesta execução. Rode de novo para continuar.")


if __name__ == "__main__":
    main()
