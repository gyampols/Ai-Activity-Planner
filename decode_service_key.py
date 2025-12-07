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
            print("Available environment variables:", [k for k in os.environ.keys() if 'GCLOUD' in k or 'GOOGLE' in k])
            sys.exit(1)
        
        print(f"Encoded key length: {len(encoded_key)} characters")
        print(f"Encoded key starts with: {encoded_key[:50]}")
        
        # Decode the base64 string
        try:
            decoded_json = base64.b64decode(encoded_key)
        except Exception as decode_error:
            print(f"ERROR: Failed to decode base64: {decode_error}")
            print(f"Encoded key type: {type(encoded_key)}")
            sys.exit(1)
        
        print(f"Decoded {len(decoded_json)} bytes")
        
        # Verify it's valid JSON by trying to parse it
        import json
        try:
            json_data = json.loads(decoded_json)
            print(f"✓ Valid JSON with {len(json_data)} keys")
        except json.JSONDecodeError as json_error:
            print(f"ERROR: Decoded data is not valid JSON: {json_error}")
            print(f"First 200 bytes of decoded data: {decoded_json[:200]}")
            sys.exit(1)
        
        # Write to file
        output_path = os.path.expanduser('~/gcloud-service-key.json')
        with open(output_path, 'wb') as f:
            f.write(decoded_json)
        
        print(f"✓ Successfully wrote service account key to {output_path}")
        
    except Exception as e:
        print(f"ERROR: Unexpected error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
