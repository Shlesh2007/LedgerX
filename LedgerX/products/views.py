from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import Product
import csv

# Create your views here.
@login_required
def product_list(request):
    """
    Shows active products with STOCK > 0.
    """
    shop = request.user.shop
    # 🟢 Filter: stock_quantity__gt=0 (Greater than 0)
    products = Product.objects.filter(
        shop=shop,
        is_active=True,
        stock_quantity__gt=0 
    ).order_by('name')

    return render(request, 'products/product_list.html', {'products': products})

@login_required
def product_out_of_stock(request):
    """
    Shows active products with STOCK == 0.
    """
    shop = request.user.shop
    # 🟢 Filter: stock_quantity=0
    products = Product.objects.filter(
        shop=shop,
        is_active=True,
        stock_quantity=0
    ).order_by('name')

    return render(request, 'products/product_out_of_stock.html', {'products': products})


@login_required
def product_add(request):
    """
    Adds a new product for the logged-in shop.
    """

    shop = request.user.shop

    if request.method == 'POST':
        name = request.POST.get('name')
        category = request.POST.get('category')
        price = request.POST.get('default_price')
        stock = request.POST.get('stock_quantity')
        img=request.FILES.get('image')
        # Basic validation
        if not name or not price or not stock:
            messages.error(request, 'All required fields must be filled')
            return redirect('product_add')

        # Create product linked to this shop
        Product.objects.create(
            shop=shop,
            name=name,
            category=category,
            default_price=price,
            stock_quantity=stock,
            image=img
        )

        messages.success(request, 'Product added successfully')
        return redirect('product_list')

    return render(request, 'products/product_add.html')


@login_required
def product_detail(request, product_id):
    """
    Shows details of a single product.
    Ensures product belongs to logged-in shop.
    """

    shop = request.user.shop

    # This ensures:
    # - product exists
    # - product belongs to this shop
    product = get_object_or_404(
        Product,
        id=product_id,
        shop=shop
    )

    return render(
        request,
        'products/product_detail.html',
        {'product': product}
    )


@login_required
def product_edit(request, product_id):
    """
    Updates an existing product.
    """

    shop = request.user.shop

    product = get_object_or_404(
        Product,
        id=product_id,
        shop=shop
    )

    if request.method == 'POST':
        product.name = request.POST.get('name')
        product.category = request.POST.get('category')
        product.default_price = request.POST.get('default_price')
        product.stock_quantity = request.POST.get('stock_quantity')
        
        if 'image' in request.FILES:
            product.image = request.FILES['image']

        product.save()

        messages.success(request, 'Product updated successfully')
        return redirect('product_list')

    return render(
        request,
        'products/product_edit.html',
        {'product': product}
    )


@login_required
def product_deactivate(request, product_id):
    """
    Soft deletes a product.
    Product remains in DB for transaction history.
    """

    shop = request.user.shop

    product = get_object_or_404(
        Product,
        id=product_id,
        shop=shop
    )

    product.is_active = False
    product.save()

    messages.info(request, 'Product removed from active list')
    return redirect('product_list')


@login_required
def export_inventory_csv(request):
    shop = request.user.shop
    products = Product.objects.filter(shop=shop, is_active=True).order_by('name')

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="inventory_export.csv"'

    # 🟢 Add the UTF-8 BOM to fix the "â‚¹" symbol in Excel
    response.write(u'\ufeff'.encode('utf8'))

    writer = csv.writer(response)
    writer.writerow(['Product Name', 'Category', 'Price (₹)', 'Stock Quantity'])

    for product in products:
        writer.writerow([
            product.name,
            product.category or 'General',
            product.default_price,
            product.stock_quantity
        ])

    return response

