export function PageHeader({ title, caption }: { title: string; caption?: string }) {
  return (
    <div className="mb-4">
      <h1 className="text-2xl font-semibold text-[#0b0b0b]">{title}</h1>
      {caption ? <p className="text-sm text-[#898781] mt-1">{caption}</p> : null}
    </div>
  );
}
