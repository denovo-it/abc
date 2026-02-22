"""Shared configuration: .env loader and RTSP camera settings."""

import os


def load_env_file(env_file='.env'):
    """Load environment variables from .env file if it exists"""
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if line and not line.startswith('#'):
                    # Parse KEY=VALUE
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        os.environ[key] = value


class RTSPConfig:
    """RTSP camera configuration"""

    @staticmethod
    def get_url():
        """Get RTSP URL with credentials from .env"""
        load_env_file()

        ip = os.getenv('RTSP_IP', '192.168.1.199')
        port = int(os.getenv('RTSP_PORT', 554))
        username = os.getenv('RTSP_USERNAME', 'sonoff')
        password = os.getenv('RTSP_PASSWORD', 'gr4jl096')
        path = os.getenv('RTSP_PATH', '/av_stream/ch0')

        return f"rtsp://{username}:{password}@{ip}:{port}{path}"
