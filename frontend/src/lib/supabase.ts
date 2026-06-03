// Optional Supabase Realtime client. The dashboard works fully via REST polling;
// when VITE_SUPABASE_URL/ANON_KEY are set, you can subscribe to table changes
// (predictions, incidents, ...) for push updates instead of polling.
import { createClient, type SupabaseClient } from "@supabase/supabase-js";

const url = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;

export const supabase: SupabaseClient | null =
  url && anonKey ? createClient(url, anonKey) : null;
