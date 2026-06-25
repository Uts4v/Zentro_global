import { supabase } from "@/lib/supabase";
import type { Session } from "@supabase/supabase-js";

export const authReady: Promise<Session | null> =
  typeof window === "undefined"
    ? Promise.resolve(null)
    : new Promise((resolve) => {
        // First try getSession() — if a session is already in localStorage
        // Supabase returns it synchronously-ish from this call
        supabase.auth.getSession().then(({ data: { session } }) => {
          if (session) {
            // Session already available — resolve immediately
            resolve(session);
            return;
          }

          // No session in getSession() yet — wait for INITIAL_SESSION event
          // This covers the case where Supabase is still reading from storage
          const {
            data: { subscription },
          } = supabase.auth.onAuthStateChange((event, s) => {
            if (event === "INITIAL_SESSION" || event === "SIGNED_IN") {
              subscription.unsubscribe();
              resolve(s);
            }
          });

          // Safety timeout — if neither fires in 4s, resolve null
          // Prevents infinite loading on broken auth state
          setTimeout(() => resolve(null), 4000);
        });
      });