import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "{{PROJECT_TITLE}} - Built with Codi",
  description: "A Next.js project created with Codi AI",
};

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-zinc-900 to-black text-white">
      <header className="pt-20 pb-12 text-center">
        <div className="flex items-center justify-center gap-4 mb-4">
          <span className="text-5xl animate-bounce">🚀</span>
          <h1 className="text-5xl font-bold bg-gradient-to-r from-indigo-500 to-purple-500 bg-clip-text text-transparent">
            {"{{PROJECT_TITLE}}"}
          </h1>
        </div>
        <p className="text-xl text-zinc-400">
          Built with <span className="text-indigo-500 font-semibold">Codi</span>
        </p>
      </header>

      <main className="max-w-6xl mx-auto px-6 pb-20">
        <div className="bg-zinc-800/50 rounded-xl p-8 mb-12 border border-indigo-500/20 hover:border-indigo-500/50 transition-all">
          <h2 className="text-2xl font-semibold mb-4 text-center">
            Get Started
          </h2>
          <p className="text-zinc-400 text-center mb-6">
            Edit <code className="bg-zinc-700 px-2 py-1 rounded">src/app/page.tsx</code> to start building
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <FeatureCard
            icon="⚡"
            title="Next.js 15"
            description="App Router with Server Components"
          />
          <FeatureCard
            icon="📘"
            title="TypeScript"
            description="Full type safety out of the box"
          />
          <FeatureCard
            icon="🎨"
            title="Tailwind CSS"
            description="Utility-first styling"
          />
        </div>
      </main>

      <footer className="text-center py-8 border-t border-zinc-800 text-zinc-500">
        <p>Created with ❤️ by Codi AI</p>
      </footer>
    </div>
  );
}

function FeatureCard({ icon, title, description }: { icon: string; title: string; description: string }) {
  return (
    <div className="bg-zinc-800/50 rounded-xl p-6 border border-zinc-700/50 hover:border-indigo-500/50 hover:-translate-y-1 transition-all">
      <span className="text-4xl block mb-4">{icon}</span>
      <h3 className="text-xl font-semibold mb-2">{title}</h3>
      <p className="text-zinc-400 text-sm">{description}</p>
    </div>
  );
}
