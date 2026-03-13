import { createClient } from '@supabase/supabase-js';

export async function runMigrations(supabaseUrl: string, supabaseKey: string) {
  const supabase = createClient(supabaseUrl, supabaseKey);
  
  const { error } = await supabase
    .from('users')
    .select('refresh_token_hash')
    .limit(1);

  if (error && error.code === '42703') {
    console.warn(
      '⚠️  Column "refresh_token_hash" missing in users table.',
      'Run: ALTER TABLE users ADD COLUMN refresh_token_hash TEXT DEFAULT NULL;',
      'in Supabase SQL Editor.',
    );
  } else {
    console.log('✅ Migration check: refresh_token_hash column exists');
  }
}
