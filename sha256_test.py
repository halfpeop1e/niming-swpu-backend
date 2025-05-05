# 假设我们在项目根目录下运行，或者 app 目录在 Python 路径中
from app.core.security import get_password_hash

# 要加密的明文密码
plain_password = "1996yong"

# 调用加密函数
hashed_password = get_password_hash(plain_password)

# 打印结果
print(f"明文密码: {plain_password}")
print(f"加密后的哈希值: {hashed_password}")

# 你还可以添加验证步骤 (可选)
from app.core.security import verify_password
is_valid = verify_password(plain_password, hashed_password)
print(f"使用 verify_password 验证结果: {is_valid}")
