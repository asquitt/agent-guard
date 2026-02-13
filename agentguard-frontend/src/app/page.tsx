export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <h1 className="text-4xl font-bold mb-4">AgentGuard</h1>
      <p className="text-xl text-muted-foreground mb-8">
        AI Agent Incident Response for Financial Services
      </p>
      <div className="flex gap-4">
        <a
          href="/login"
          className="px-6 py-3 bg-primary text-white rounded-lg hover:bg-primary/80"
        >
          Login
        </a>
        <a
          href="/register"
          className="px-6 py-3 border border-primary text-primary rounded-lg hover:bg-primary/10"
        >
          Register
        </a>
      </div>
    </main>
  );
}
