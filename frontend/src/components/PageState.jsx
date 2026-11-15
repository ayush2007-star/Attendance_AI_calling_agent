import Notice from "./Notice";

export default function PageState({ loading, error, children }) {
  if (loading) return <p className="page-state">Loading your data…</p>;
  if (error) return <Notice>{error}</Notice>;
  return children;
}
