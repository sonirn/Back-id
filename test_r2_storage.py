#!/usr/bin/env python3
"""
Simple R2 Storage Test
Tests the R2 storage functionality directly
"""

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
import os
import tempfile
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')

def test_r2_storage():
    """Test R2 storage directly"""
    print("=== Testing R2 Storage Directly ===")
    
    try:
        # Get R2 configuration
        endpoint_url = os.environ.get('CLOUDFLARE_API_ENDPOINT')
        access_key = os.environ.get('CLOUDFLARE_ACCESS_KEY')
        secret_key = os.environ.get('CLOUDFLARE_SECRET_KEY')
        
        if not all([endpoint_url, access_key, secret_key]):
            print("❌ R2 environment variables not configured")
            return False
        
        print(f"R2 Endpoint: {endpoint_url}")
        
        # Create S3 client for R2
        s3_client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(signature_version='s3v4')
        )
        
        # Test bucket operations
        bucket_name = "video-generation-bucket"
        
        # Try to create bucket if it doesn't exist
        try:
            s3_client.head_bucket(Bucket=bucket_name)
            print(f"✅ Bucket '{bucket_name}' exists")
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                try:
                    s3_client.create_bucket(Bucket=bucket_name)
                    print(f"✅ Created bucket '{bucket_name}'")
                except ClientError as create_error:
                    print(f"❌ Failed to create bucket: {create_error}")
                    return False
            else:
                print(f"❌ Error checking bucket: {e}")
                return False
        
        # Test file upload
        test_content = "Test file content for R2 storage"
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
        temp_file.write(test_content)
        temp_file.close()
        
        try:
            # Upload test file
            test_key = "test/test_file.txt"
            s3_client.upload_file(temp_file.name, bucket_name, test_key)
            print("✅ File uploaded successfully")
            
            # Try to list objects
            response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix="test/")
            if 'Contents' in response:
                print(f"✅ File listing works - found {len(response['Contents'])} objects")
            
            # Clean up test file
            s3_client.delete_object(Bucket=bucket_name, Key=test_key)
            print("✅ File cleanup successful")
            
            return True
            
        except ClientError as e:
            print(f"❌ File operations failed: {e}")
            return False
        finally:
            os.unlink(temp_file.name)
            
    except Exception as e:
        print(f"❌ R2 storage test failed: {str(e)}")
        return False

if __name__ == "__main__":
    test_r2_storage()