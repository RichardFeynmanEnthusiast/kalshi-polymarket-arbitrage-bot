from supabase import create_client, Client

class SupabaseClient:
    """
       A wrapper client for interacting with Supabase.

       Attributes:
           supabase_url (str): The URL of the Supabase project.
           supabase_anon_key (str): The anonymous public API key for Supabase.
           client (Client): The Supabase client instance created with the URL and anon key.
       """
    def __init__(self, supabase_url : str, supabase_anon_key : str):
        """
                Initialize the SupabaseClient with project URL and anon key.

                Args:
                    supabase_url (str): The URL endpoint of the Supabase project.
                    supabase_anon_key (str): The anon public API key for authentication.
                """
        self.supabase_url = supabase_url
        self.supabase_anon_key = supabase_anon_key
        try:
            self.client : Client = create_client(supabase_url=self.supabase_url, supabase_key=self.supabase_anon_key)
        except Exception as e:
            raise RuntimeError(f"Failed to create Supabase client: {e}")