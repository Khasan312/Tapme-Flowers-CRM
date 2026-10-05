from tapme.catalog.domain import Product
from tapme.catalog.models import ProductRecord
from tapme.shared.domain import Conflict, NotFound, Page


def to_domain(row):
    return Product(row.id, row.business_id, row.name, row.price, row.version, row.active)


class DjangoProductRepository:
    def get(self, business_id, product_id):
        row = ProductRecord.objects.filter(business_id=business_id, id=product_id).first()
        if row is None:
            raise NotFound("Позиция прайса не найдена.")
        return to_domain(row)

    def add(self, product):
        ProductRecord.objects.create(
            id=product.id, business_id=product.business_id, name=product.name, price=product.price
        )
        return product

    def list(self, business_id, limit, offset, include_hidden=False):
        query = ProductRecord.objects.filter(business_id=business_id).order_by("name", "id")
        if not include_hidden:
            query = query.filter(active=True)
        return Page(tuple(to_domain(r) for r in query[offset : offset + limit]), query.count())

    def save(self, product, expected_version):
        changed = ProductRecord.objects.filter(
            id=product.id, business_id=product.business_id, version=expected_version
        ).update(
            name=product.name, price=product.price, version=product.version, active=product.active
        )
        if not changed:
            raise Conflict("Позиция уже изменена. Обновите прайс.")
        return product
