from enum import Enum, unique


@unique
class RedisKey(str, Enum):
    FILE_STORAGE_METADATA = "file_storage:meta:{}:{}"
    UPLOAD_FILE_CHUNKS_BITMAP = "upload:bitmap:{}:{}"
    FILE_VECTORIZATION_TASK_STATUS = "vector:task:{}"
    FILE_VECTORIZATION_TASK_ERROR = "vector:task:error:{}"
    FILE_VECTORIZATION_TASK_STAGE = "vector:task:stage:{}"
    FILE_VECTORIZATION_TASK_ERROR_CODE = "vector:task:error:code:{}"
    FILE_VECTORIZATION_TASK_ERROR_MESSAGE = "vector:task:error:message:{}"
    FILE_VECTORIZATION_TASK_RETRYABLE = "vector:task:retryable:{}"
    FILE_VECTORIZATION_TASK_UPDATED_AT = "vector:task:updated_at:{}"
    FILE_VECTORIZATION_TASK_CURSOR = "vector:cursor:{}"
    USER_SESSION = "auth:session:{}"


@unique
class MilvusField(str, Enum):
    PK = "pk"
    FILE_ID = "file_id"
    FILE_MD5 = "file_md5"
    CHUNK_INDEX = "chunk_index"
    PAGE_NO = "page_no"
    SECTION = "section"
    CONTENT = "content"
    SPARSE_VECTOR = "sparse_vector"
    DENSE_VECTOR = "dense_vector"
    METADATA = "metadata"
