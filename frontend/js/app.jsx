/* App shell — top nav, tab routing, theme + shared repository state.

   Integrated with UserProvider for email-based authentication.
   Repository data is loaded from backend based on user.
*/

function useTheme() {
  const [theme, setTheme] = useState(() => {
    try { return localStorage.getItem("sdv-theme") === "dark" ? "dark" : "light"; } catch (e) { return "light"; }
  });
  useEffect(() => {
    const root = document.documentElement;
    if (theme === "dark") root.classList.add("dark"); else root.classList.remove("dark");
    try { localStorage.setItem("sdv-theme", theme); } catch (e) { }
  }, [theme]);
  return [theme, setTheme];
}

function NavTab({ active, onClick, icon, children }) {
  return (
    <button
      onClick={onClick}
      className={`relative inline-flex items-center gap-2 rounded-lg px-3.5 py-2 text-sm font-medium transition ${active
          ? "bg-white text-slate-900 shadow-card dark:bg-slate-800 dark:text-white"
          : "text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200"
        }`}
    >
      {icon}{children}
    </button>
  );
}

function AppContent() {
  const { user, logout, updatePuzzleCount, analyticsUnlocked, puzzleCount } = useUser();
  const [theme, setTheme] = useTheme();
  const [page, setPage] = useState("submit");
  const [repo, setRepo] = useState([]);
  const [loading, setLoading] = useState(true);

  // Load user's puzzles from backend
  useEffect(() => {
    if (!user) {
      setRepo([]);
      setLoading(false);
      return;
    }

    setLoading(true);
    fetch(`${window.API_BASE_URL}/api/repository?user_id=${user.userId}`)
      .then(res => res.json())
      .then(data => {
        setRepo(data.puzzles || []);
      })
      .catch(err => {
        console.error("Failed to load repository:", err);
        setRepo([]);
      })
      .finally(() => setLoading(false));
  }, [user?.userId]);

  const addRecord = async (rec) => {
    try {
      const res = await fetch(`${window.API_BASE_URL}/api/submit-puzzle?user_id=${user.userId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(rec)
      });
      const result = await res.json();

      if (result.success) {
        // Add to local state
        setRepo(prev => [{ id: result.id, ...rec }, ...prev]);
        // Update user context with new puzzle count
        updatePuzzleCount(result.puzzleCount);
        // Navigate to repository
        setPage("repository");
        return result;
      } else if (result.error === "duplicate") {
        return { success: false, error: "duplicate", message: "This puzzle has already been submitted." };
      }
      return result;
    } catch (err) {
      console.error("Failed to submit puzzle:", err);
      return { success: false, error: "network", message: "Failed to save puzzle. Please try again." };
    }
  };

  // Show email prompt if not authenticated
  if (!user) {
    return <EmailPrompt />;
  }

  return (
    <div className="min-h-screen">
      {/* top nav */}
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/85 backdrop-blur-md dark:border-slate-800 dark:bg-slate-950/80">
        <div className="mx-auto flex max-w-[1180px] items-center justify-between gap-4 px-5 py-3 lg:px-8">
          <Logo />
          <nav className="hidden items-center gap-1 rounded-xl bg-slate-100 p-1 dark:bg-slate-900 sm:flex">
            <NavTab active={page === "submit"} onClick={() => setPage("submit")} icon={<Icon.grid />}>Submit puzzle</NavTab>
            <NavTab active={page === "repository"} onClick={() => setPage("repository")} icon={<Icon.chart />}>Repository &amp; Analytics</NavTab>
          </nav>
          <div className="flex items-center gap-2">
            {/* Puzzle count badge */}
            <div className="hidden items-center gap-1.5 rounded-md bg-accent-50 px-2.5 py-1 dark:bg-accent-500/10 md:flex">
              <span className="h-1.5 w-1.5 rounded-full bg-accent-500"></span>
              <span className="font-mono text-[11px] text-accent-700 dark:text-accent-300 tnum">{puzzleCount} puzzles</span>
              {!analyticsUnlocked && (
                <span className="text-[10px] text-slate-400">({MIN_FOR_ANALYTICS - puzzleCount} more for analytics)</span>
              )}
            </div>
            {/* User menu */}
            <div className="hidden items-center gap-2 md:flex">
              <span className="text-xs text-slate-500 dark:text-slate-400 truncate max-w-[120px]" title={user.email}>
                {user.email}
              </span>
              <button
                onClick={logout}
                className="text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition"
                title="Sign out"
              >
                <Icon.logout />
              </button>
            </div>
            <ThemeToggle theme={theme} setTheme={setTheme} />
          </div>
        </div>
        {/* mobile tabs */}
        <nav className="flex items-center justify-between border-t border-slate-100 px-3 py-2 dark:border-slate-800 sm:hidden">
          <div className="flex items-center gap-1">
            <NavTab active={page === "submit"} onClick={() => setPage("submit")} icon={<Icon.grid />}>Submit</NavTab>
            <NavTab active={page === "repository"} onClick={() => setPage("repository")} icon={<Icon.chart />}>Repository</NavTab>
          </div>
          <button
            onClick={logout}
            className="text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 p-2"
            title="Sign out"
          >
            <Icon.logout />
          </button>
        </nav>
      </header>

      <main>
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="flex items-center gap-3 text-slate-500">
              <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              Loading your puzzles...
            </div>
          </div>
        ) : (
          page === "submit" ? <SubmitPage addRecord={addRecord} /> : <RepositoryPage repo={repo} />
        )}
      </main>

      <footer className="mx-auto max-w-[1180px] px-5 pb-10 pt-4 lg:px-8">
        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-200 pt-4 font-mono text-[11px] text-slate-400 dark:border-slate-800">
          <span>Sudoku Research Platform — logical-technique grading engine</span>
          <span>Naked/Hidden Singles · Locked Candidates · Pairs/Triples · X-Wing · XY-Wing</span>
        </div>
      </footer>
    </div>
  );
}

function App() {
  return (
    <UserProvider>
      <AppContent />
    </UserProvider>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
