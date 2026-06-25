import { supabase } from "@/lib/supabase";
import type { Session } from "@supabase/supabase-js";

// On the server there's no localStorage, so we just resolve with null immediately.
// The real auth check happens client-side after hydration.
export const authReady: Promise<Session | null> =
  typeof window === "undefined"
    ? Promise.resolve(null)
    : new Promise((resolve) => {
        const {
          data: { subscription },
        } = supabase.auth.onAuthStateChange((event, session) => {
          if (event === "INITIAL_SESSION") {
            subscription.unsubscribe();
            resolve(session);
          }
        });
      });