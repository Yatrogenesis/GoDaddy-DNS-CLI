"""
Interactive shell for GoDaddy DNS CLI
"""

import cmd
import sys
from typing import Optional

from godaddy_cli.core.config import ConfigManager
from godaddy_cli.core.auth import AuthManager


class InteractiveShell(cmd.Cmd):
    """Interactive shell for GoDaddy DNS CLI"""

    intro = 'Welcome to GoDaddy DNS CLI interactive shell. Type help or ? to list commands.\n'
    prompt = 'godaddy> '

    def __init__(self, config_manager: ConfigManager, auth_manager: AuthManager):
        super().__init__()
        self.config_manager = config_manager
        self.auth_manager = auth_manager

    def do_exit(self, arg):
        """Exit the shell"""
        print("Goodbye!")
        return True

    def do_quit(self, arg):
        """Exit the shell"""
        return self.do_exit(arg)

    def do_EOF(self, arg):
        """Handle EOF (Ctrl+D)"""
        print()
        return self.do_exit(arg)

    def do_status(self, arg):
        """Show current status"""
        current_profile = self.config_manager.current_profile
        print(f"Current profile: {current_profile}")

        creds = self.auth_manager.get_credentials(current_profile)
        if creds:
            print(f"API Key: {creds.api_key[:8]}...")
            print("Authentication: Configured")
        else:
            print("Authentication: Not configured")

    def do_profiles(self, arg):
        """List available profiles"""
        profiles = self.config_manager.list_profiles()
        current = self.config_manager.current_profile

        print("Available profiles:")
        for profile in profiles:
            marker = " (current)" if profile == current else ""
            print(f"  {profile}{marker}")

    def run(self):
        """Run the interactive shell"""
        try:
            self.cmdloop()
        except KeyboardInterrupt:
            print("\nUse 'exit' or 'quit' to leave the shell.")
            self.run()