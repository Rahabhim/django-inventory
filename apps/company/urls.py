from models import Department, DepartmentType
from common.helpers import auto_urls

urlpatterns = auto_urls(Department, DepartmentType)

#eof