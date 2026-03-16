import os
import json
import logging
from core.db import execute, execute_one
from core.config import *

def index_tenant(tenant_id: str):
    products = list_products(tenant_id)
    # index each product
