# import mimetypes
# from urllib.parse import unquote, urlparse

# import boto3
# import frappe
# from frappe import _
# from botocore.exceptions import ClientError

# def get_s3_config():
# 	"""
# 	Returns S3 configuration from site config.
# 	Expects 'file_system_storage' key in site_config.json.
# 	"""
# 	config = frappe.conf.get("file_system_storage")
# 	if not config:
# 		frappe.throw(_("File System Storage configuration not found in site_config.json"))
# 	return config

# def get_s3_client():
# 	"""
# 	Returns a boto3 S3 client using credentials from site config.
# 	"""
# 	config = get_s3_config()
# 	if not config.get("enabled"):
# 		return None
		
# 	return boto3.client(
# 		"s3",
# 		aws_access_key_id=config.get("access_key"),
# 		aws_secret_access_key=config.get("secret_key"),
# 		endpoint_url=config.get("endpoint_url"),
# 		region_name=config.get("region") or "auto",
# 	)

# def get_bucket_name():
# 	config = get_s3_config()
# 	return config.get("bucket_name")

# def upload_file_to_gcs(*args, **kwargs):
# 	"""
# 	Uploads a file to Google Cloud Storage (via S3 API).
# 	Hook for: write_file
# 	Handles two signatures:
# 	1. (file_doc) - called from File.save_file
# 	2. (fname, content, content_type, is_private) - called from file_manager.save_file
# 	"""
# 	fname = None
# 	content = None
# 	content_type = None
# 	is_private = 0
	
# 	if len(args) == 1 and hasattr(args[0], "doctype") and args[0].doctype == "File":
# 		# Case 1: Called with File document
# 		file_doc = args[0]
# 		fname = file_doc.file_name
# 		content = file_doc.get_content()
# 		content_type = file_doc.file_type
# 		is_private = file_doc.is_private
# 	elif len(args) >= 2:
# 		# Case 2: Called with individual arguments
# 		fname = args[0]
# 		content = args[1]
# 		content_type = args[2] if len(args) > 2 else kwargs.get("content_type")
# 		is_private = args[3] if len(args) > 3 else kwargs.get("is_private", 0)
# 	else:
# 		# Try kwargs
# 		fname = kwargs.get("fname")
# 		content = kwargs.get("content")
# 		content_type = kwargs.get("content_type")
# 		is_private = kwargs.get("is_private", 0)
		
# 	if not fname or content is None:
# 		frappe.throw(_("Missing file name or content for GCS upload"))

# 	try:
# 		client = get_s3_client()
# 		if not client:
# 			# If disabled, fallback to local filesystem
# 			from frappe.utils.file_manager import save_file_on_filesystem
# 			return save_file_on_filesystem(fname, content, content_type, is_private)
		
# 		s3 = client
# 		bucket_name = get_bucket_name()
		
# 		if not content_type:
# 			content_type, encoding = mimetypes.guess_type(fname)
		
# 		params = {
# 			"Bucket": bucket_name,
# 			"Key": fname,
# 			"Body": content,
# 			"ContentType": content_type or "application/octet-stream",
# 		}
# 		s3.put_object(**params)
		
# 		# Construct URL
# 		endpoint = get_s3_config().get("endpoint_url")
# 		if endpoint.endswith("/"):
# 			endpoint = endpoint[:-1]
			
# 		file_url = f"{endpoint}/{bucket_name}/{fname}"

# 		# Important: If called with a File document, update it in-place!
# 		# Frappe's File.save_file ignores the return value, so we must update the doc.
# 		if len(args) == 1 and hasattr(args[0], "doctype") and args[0].doctype == "File":
# 			file_doc = args[0]
# 			file_doc.file_url = file_url
# 			file_doc.file_size = len(content)

# 		return {
# 			"file_name": fname,
# 			"file_url": file_url
# 		}

# 	except Exception as e:
# 		frappe.log_error("S3 Upload Failed", str(e))
# 		raise e

# def delete_file_from_gcs(doc, only_thumbnail=False):
# 	"""
# 	Deletes a file from Google Cloud Storage (via S3 API).
# 	Hook for: delete_file_data_content
# 	"""
# 	try:
# 		client = get_s3_client()
# 		if not client:
# 			from frappe.utils.file_manager import delete_file_from_filesystem
# 			return delete_file_from_filesystem(doc, only_thumbnail)

# 		s3 = client
# 		bucket_name = get_bucket_name()
# 		if only_thumbnail:
# 			return

# 		object_key = None
# 		for candidate in [getattr(doc, "file_name", None), getattr(doc, "file_url", None)]:
# 			if not candidate:
# 				continue

# 			if "://" in candidate:
# 				parsed = urlparse(candidate)
# 				path = unquote(parsed.path.lstrip("/"))
# 				if path.startswith(f"{bucket_name}/"):
# 					path = path[len(bucket_name) + 1 :]
# 				elif path.startswith("files/") or path.startswith("private/files/"):
# 					path = path.split("/", 1)[1]
# 				object_key = path
# 			else:
# 				object_key = candidate.strip("/")

# 			if object_key:
# 				break

# 			if not object_key:
# 				frappe.throw(_("Unable to determine object key for remote file deletion"))

# 		s3.delete_object(Bucket=bucket_name, Key=object_key)

# 		# Thumbnail deletion logic if applicable
# 		# if doc.thumbnail_url: ...

# 	except Exception as e:
# 		frappe.log_error("S3 Delete Failed", f"{str(e)} | key={object_key if 'object_key' in locals() else None}")
# 		raise




import mimetypes
from urllib.parse import unquote, urlparse

import boto3
import frappe
from frappe import _
from botocore.exceptions import ClientError

def get_s3_config():
	"""
	Returns S3 configuration from site config.
	Expects 'file_system_storage' key in site_config.json.
	"""
	config = frappe.conf.get("file_system_storage")
	if not config:
		frappe.throw(_("File System Storage configuration not found in site_config.json"))
	return config

def get_s3_client():
	"""
	Returns a boto3 S3 client using credentials from site config.
	"""
	config = get_s3_config()
	if not config.get("enabled"):
		return None
		
	return boto3.client(
		"s3",
		aws_access_key_id=config.get("access_key"),
		aws_secret_access_key=config.get("secret_key"),
		endpoint_url=config.get("endpoint_url"),
		region_name=config.get("region") or "auto",
	)

def get_bucket_name():
	config = get_s3_config()
	return config.get("bucket_name")

def upload_file_to_gcs(*args, **kwargs):
	"""
	Uploads a file to Google Cloud Storage (via S3 API).
	Hook for: write_file
	Handles two signatures:
	1. (file_doc) - called from File.save_file
	2. (fname, content, content_type, is_private) - called from file_manager.save_file
	"""
	fname = None
	content = None
	content_type = None
	is_private = 0
	attached_to_doctype = None
	attached_to_name = None
	
	if len(args) == 1 and hasattr(args[0], "doctype") and args[0].doctype == "File":
		# Case 1: Called with File document
		file_doc = args[0]
		fname = file_doc.file_name
		content = file_doc.get_content()
		content_type = file_doc.file_type
		is_private = file_doc.is_private
		attached_to_doctype = file_doc.attached_to_doctype
		attached_to_name = file_doc.attached_to_name
	elif len(args) >= 2:
		# Case 2: Called with individual arguments
		fname = args[0]
		content = args[1]
		content_type = args[2] if len(args) > 2 else kwargs.get("content_type")
		is_private = args[3] if len(args) > 3 else kwargs.get("is_private", 0)
		attached_to_doctype = frappe.form_dict.get("doctype")
		attached_to_name = frappe.form_dict.get("docname")
	else:
		# Try kwargs
		fname = kwargs.get("fname")
		content = kwargs.get("content")
		content_type = kwargs.get("content_type")
		is_private = kwargs.get("is_private", 0)
		attached_to_doctype = kwargs.get("attached_to_doctype") or frappe.form_dict.get("doctype")
		attached_to_name = kwargs.get("attached_to_name") or frappe.form_dict.get("docname")
		
	if not fname or content is None:
		frappe.throw(_("Missing file name or content for GCS upload"))

	parts = [p.strip().replace(" ", "-") for p in (attached_to_doctype, attached_to_name) if p]
	if parts:
		prefix = "-".join(parts)
		if not fname.startswith(f"{prefix}-"):
			fname = f"{prefix}-{fname}"

	try:
		client = get_s3_client()
		if not client:
			# If disabled, fallback to local filesystem
			from frappe.utils.file_manager import save_file_on_filesystem
			return save_file_on_filesystem(fname, content, content_type, is_private)
		
		s3 = client
		bucket_name = get_bucket_name()
		# Resolve standard lowercase MIME type (e.g., application/pdf)
		mime_type = None
		if fname:
			mime_type, _ = mimetypes.guess_type(fname)
		if not mime_type and content_type:
			if "/" in content_type:
				mime_type = content_type
			else:
				mime_type, _ = mimetypes.guess_type(f"dummy.{content_type.lower()}")
		mime_type = mime_type or "application/octet-stream"
		
		params = {
			"Bucket": bucket_name,
			"Key": fname,
			"Body": content,
			"ContentType": mime_type,
		}
		s3.put_object(**params)
		
		# Construct URL
		config = get_s3_config()
		public_url = config.get("public_dev_url")
		if public_url:
			if public_url.endswith("/"):
				public_url = public_url[:-1]
			file_url = f"{public_url}/{fname}"
		else:
			endpoint = config.get("endpoint_url")
			if endpoint.endswith("/"):
				endpoint = endpoint[:-1]
			file_url = f"{endpoint}/{bucket_name}/{fname}"

		# Important: If called with a File document, update it in-place!
		# Frappe's File.save_file ignores the return value, so we must update the doc.
		if len(args) == 1 and hasattr(args[0], "doctype") and args[0].doctype == "File":
			file_doc = args[0]
			file_doc.file_name = fname
			file_doc.file_url = file_url
			file_doc.file_size = len(content)

		return {
			"file_name": fname,
			"file_url": file_url
		}

	except Exception as e:
		frappe.log_error("S3 Upload Failed", str(e))
		raise e

def delete_file_from_gcs(doc, only_thumbnail=False):
	"""
	Deletes a file from Google Cloud Storage (via S3 API).
	Hook for: delete_file_data_content
	"""
	try:
		client = get_s3_client()
		if not client:
			from frappe.utils.file_manager import delete_file_from_filesystem
			return delete_file_from_filesystem(doc, only_thumbnail)

		s3 = client
		bucket_name = get_bucket_name()
		if only_thumbnail:
			return

		object_key = None
		for candidate in [getattr(doc, "file_name", None), getattr(doc, "file_url", None)]:
			if not candidate:
				continue

			if "://" in candidate:
				parsed = urlparse(candidate)
				path = unquote(parsed.path.lstrip("/"))
				if path.startswith(f"{bucket_name}/"):
					path = path[len(bucket_name) + 1 :]
				elif path.startswith("files/") or path.startswith("private/files/"):
					path = path.split("/", 1)[1]
				object_key = path
			else:
				object_key = candidate.strip("/")

			if object_key:
				break

			if not object_key:
				frappe.throw(_("Unable to determine object key for remote file deletion"))

		s3.delete_object(Bucket=bucket_name, Key=object_key)

		# Thumbnail deletion logic if applicable
		# if doc.thumbnail_url: ...

	except Exception as e:
		frappe.log_error("S3 Delete Failed", f"{str(e)} | key={object_key if 'object_key' in locals() else None}")
		raise

