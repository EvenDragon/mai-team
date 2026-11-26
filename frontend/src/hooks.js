import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";
export function useResource(path, identity = "") {
  const [version, setVersion] = useState(0);
  const [state, setState] = useState({ data: null, error: "", loading: true });
  useEffect(() => {
    const controller = new AbortController();
    setState({ data: null, error: "", loading: true });
    api(path, { signal: controller.signal })
      .then((data) => {
        if (!controller.signal.aborted)
          setState({ data, error: "", loading: false });
      })
      .catch((error) => {
        if (!controller.signal.aborted)
          setState({ data: null, error: error.message, loading: false });
      });
    return () => controller.abort();
  }, [path, version, identity]);
  const reload = useCallback(() => setVersion((v) => v + 1), []);
  return { ...state, reload };
}
export function useAction() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const running = useRef(false);
  async function run(fn, message = "") {
    if (running.current) return;
    running.current = true;
    setBusy(true);
    setError("");
    setSuccess("");
    try {
      await fn();
      setSuccess(message);
    } catch (e) {
      setError(e.message);
    } finally {
      running.current = false;
      setBusy(false);
    }
  }
  return { busy, error, success, run };
}
