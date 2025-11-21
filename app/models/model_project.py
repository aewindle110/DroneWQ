class project:
    def __init__(
        self,
        id,
        name,
        folder_path,
        data_source,
        created_at,
        lw_method,
        ed_method,
        mask_method,
        wq_algs,
        mosaic,
    ):
        self.id = id
        self.name = name
        self.folder_path = folder_path
        self.data_source = data_source
        self.created_at = created_at
        self.lw_method = lw_method
        self.ed_method = ed_method
        self.mask_method = mask_method
        self.wq_algs = wq_algs
        self.mosaic = mosaic
