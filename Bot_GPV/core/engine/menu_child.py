class MenuChild:
    def __init__(self, path_name, url, module_name):
        self.path_name = path_name  # Ví dụ: "Thiết lập | Chi nhánh"
        self.name = path_name.split('|')[-1].strip() # Lấy tên cuối: "Chi nhánh"
        self.url = url
        self.module_name = module_name
        self.metadata = {}

    def to_dict(self):
        return {
            "name": self.name,
            "path": self.path_name,
            "url": self.url,
            "module": self.module_name,
            "interface": self.metadata,
            "status": "Hoàn tất nội soi"
        }