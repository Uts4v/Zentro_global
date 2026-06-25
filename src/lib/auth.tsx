import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import { supabase } from "@/lib/supabase";
import type { User, Session } from "@supabase/supabase-js";

type Profile = {
  id: string;
  full_name: string | null;
  avatar_url: string | null;
  points: number;
  streak: number;
  tier: string;
  role?: "customer" | "merchant";
};

type MerchantProfile = {
  id: string;
  user_id: string;
  store_name: string;
  store_slug: string | null;
  business_type: string | null;
  address: string | null;
  phone: string | null;
  logo_url: string | null;
  banner_url: string | null;
  is_approved: boolean;
  created_at: string;
};

type SignUpMeta = {
  role?: "customer" | "merchant";
  store_name?: string;
};

type AuthContextType = {
  user: User | null;
  session: Session | null;
  profile: Profile | null;
  merchantProfile: MerchantProfile | null;
  loading: boolean;
  signUp: (
    email: string,
    password: string,
    name: string,
    meta?: SignUpMeta
  ) => Promise<{ error: string | null }>;
  signIn: (
    email: string,
    password: string
  ) => Promise<{ error: string | null }>;
  signOut: () => Promise<void>;
  refreshProfile: () => Promise<void>;
  refreshMerchantProfile: () => Promise<void>;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [merchantProfile, setMerchantProfile] =
    useState<MerchantProfile | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchProfile = useCallback(async (userId: string) => {
    try {
      const { data, error } = await supabase
        .from("profiles")
        .select("*")
        .eq("id", userId)
        .maybeSingle();

      if (error || !data) {
        setProfile({
          id: userId,
          full_name: null,
          avatar_url: null,
          points: 0,
          streak: 0,
          tier: "Bronze",
        });
        return;
      }
      setProfile(data as Profile);
    } catch {
      setProfile({
        id: userId,
        full_name: null,
        avatar_url: null,
        points: 0,
        streak: 0,
        tier: "Bronze",
      });
    }
  }, []);

  const fetchMerchantProfile = useCallback(async (userId: string) => {
    try {
      const { data, error } = await supabase
        .from("merchant_profiles")
        .select("*")
        .eq("user_id", userId)
        .maybeSingle();

      if (error || !data) {
        setMerchantProfile(null);
        return;
      }
      setMerchantProfile(data as MerchantProfile);
    } catch {
      setMerchantProfile(null);
    }
  }, []);

  const refreshProfile = useCallback(async () => {
    if (user?.id) {
      await fetchProfile(user.id);
    }
  }, [user, fetchProfile]);

  const refreshMerchantProfile = useCallback(async () => {
    if (user?.id) {
      await fetchMerchantProfile(user.id);
    }
  }, [user, fetchMerchantProfile]);

  // ─── Single unified effect ────────────────────────────────────────────────
  // Previously this was accidentally split into TWO useEffect calls, which
  // meant onAuthStateChange and its cleanup `return` were floating outside
  // any effect entirely — causing the subscription to never be cleaned up
  // and the auth listener to silently not work.
  useEffect(() => {
    // 1. Restore session on mount
    supabase.auth.getSession().then(({ data: { session: s } }) => {
      setSession(s);
      setUser(s?.user ?? null);
      if (s?.user) {
        fetchProfile(s.user.id);
        if (s.user.user_metadata?.role === "merchant") {
          fetchMerchantProfile(s.user.id);
        }
      }
      setLoading(false);
    });

    // 2. Keep state in sync on every auth event (sign-in, sign-out, token refresh)
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, s) => {
      setSession(s);
      setUser(s?.user ?? null);
      if (s?.user) {
        fetchProfile(s.user.id);
        if (s.user.user_metadata?.role === "merchant") {
          fetchMerchantProfile(s.user.id);
        } else {
          setMerchantProfile(null);
        }
      } else {
        setProfile(null);
        setMerchantProfile(null);
      }
    });

    // 3. Clean up the listener when the provider unmounts
    return () => subscription.unsubscribe();
  }, [fetchProfile, fetchMerchantProfile]); // ← both deps included

  // ─── Sign up ──────────────────────────────────────────────────────────────
  const signUp = useCallback(
    async (
      email: string,
      password: string,
      name: string,
      meta?: SignUpMeta
    ) => {
      const role = meta?.role || "customer";
      const { error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: {
            full_name: name,
            role,
            ...(meta?.store_name ? { store_name: meta.store_name } : {}),
          },
        },
      });

      if (error) return { error: error.message };

      const {
        data: { user: currentUser },
      } = await supabase.auth.getUser();

      if (currentUser) {
        await supabase.from("profiles").upsert({
          id: currentUser.id,
          full_name: name,
          points: 0,
          streak: 0,
          tier: "Bronze",
          role,
        });

        if (role === "merchant" && meta?.store_name) {
          await supabase.from("merchant_profiles").insert({
            user_id: currentUser.id,
            store_name: meta.store_name,
            store_slug: meta.store_name
              .toLowerCase()
              .replace(/[^a-z0-9]+/g, "-")
              .replace(/(^-|-$)/g, ""),
            is_approved: false,
          });
        }
      }

      return { error: null };
    },
    []
  );

  // ─── Sign in ──────────────────────────────────────────────────────────────
  const signIn = useCallback(async (email: string, password: string) => {
    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    if (error) return { error: error.message };
    return { error: null };
  }, []);

  // ─── Sign out ─────────────────────────────────────────────────────────────
  const signOut = useCallback(async () => {
    await supabase.auth.signOut();
    setUser(null);
    setSession(null);
    setProfile(null);
    setMerchantProfile(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        session,
        profile,
        merchantProfile,
        loading,
        signUp,
        signIn,
        signOut,
        refreshProfile,
        refreshMerchantProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}