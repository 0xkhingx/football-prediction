import Link from "next/link";

export default function NotFound() {
  return (
    <div className="space-y-3">
      <section className="rounded-[2rem] bg-cream px-6 py-16 text-center sm:px-12">
        <p className="font-mono text-[11px] tracking-[0.3em] text-ember">404</p>
        <h1 className="mt-2 font-display text-5xl uppercase leading-none text-ember sm:text-7xl">
          No such fixture
        </h1>
        <p className="mx-auto mt-4 max-w-md text-sm leading-relaxed text-coal/70">
          This page never kicked off. Back to the ties that actually exist.
        </p>
        <div className="mt-8">
          <Link
            href="/"
            className="inline-flex items-center gap-4 rounded-full bg-coal py-2 pl-8 pr-2 font-mono text-xs tracking-[0.25em] text-cream"
          >
            BACK TO FIXTURES
            <span
              aria-hidden="true"
              className="flex h-10 w-10 items-center justify-center rounded-full bg-cream text-coal"
            >
              →
            </span>
          </Link>
        </div>
      </section>
    </div>
  );
}
