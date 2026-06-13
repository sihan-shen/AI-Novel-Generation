export default function Dashboard() {
  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold tracking-tight">Novel Forge</h1>
      <p className="mt-2 text-zinc-500 dark:text-zinc-400">
        欢迎回来，继续你的创作之旅。
      </p>

      <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <QuickCard
          title="最近项目"
          desc="查看和管理你的小说项目"
          href="/projects"
        />
        <QuickCard
          title="灵感记录"
          desc="随手记录创作灵感"
          href="/ideas"
        />
        <QuickCard
          title="文风库"
          desc="管理和分析参考文风"
          href="/styles"
        />
      </div>
    </div>
  );
}

function QuickCard({
  title,
  desc,
  href,
}: {
  title: string;
  desc: string;
  href: string;
}) {
  return (
    <a
      href={href}
      className="block rounded-lg border p-6 transition-colors hover:bg-zinc-50 dark:hover:bg-zinc-900"
    >
      <h3 className="font-semibold">{title}</h3>
      <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">{desc}</p>
    </a>
  );
}
