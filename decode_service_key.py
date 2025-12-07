#!/usr/bin/env python3
"""
Decode base64-encoded Google Cloud service account key from environment variable.
Used by CircleCI for deployment authentication.
"""
import base64
import os
import sys

def main():
    try:
        # Get the base64 encoded key from environment
        encoded_key = os.environ.get('GCLOUD_SERVICE_KEY', '')
        
        if not encoded_key:
            print("ERROR: GCLOUD_SERVICE_KEY environment variable is empty")
            sys.exit(1)
        
        print(f"Encoded key length: {len(encoded_key)} characters")
        
        # Decode the base64 string
        decoded_json = base64.b64decode(encoded_key)
        
        # Write to file
        output_path = os.path.expanduser('~/gcloud-service-key.json')
        with open(output_path, 'wb') as f:
            f.write(decoded_json)
        
        print(f"✓ Successfully decoded {len(decoded_json)} bytes to {output_path}")
        
    except Exception as e:
        print(f"ERROR: Failed to decode service account key: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
