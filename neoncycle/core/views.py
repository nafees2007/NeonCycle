import random
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required

from .models import UserProfile, GarbagePrice, CollectionOrder, RecyclerDemand, RecycledProduct
from .ai_scanner import forecast_garbage_price


def ensure_initial_prices():
    """Ensures the 5 core garbage categories exist for the live stock ticker."""
    if GarbagePrice.objects.count() == 0:
        defaults = [
            ('Plastic (PET)', 'PLASTIC', 42.0, 3.8),
            ('E-Waste', 'EWASTE', 310.0, 8.4),
            ('Metal & Copper', 'METAL', 480.0, 5.1),
            ('Paper & Cardboard', 'PAPER', 18.0, -1.2),
            ('Glass Bottles', 'GLASS', 14.0, 1.5),
        ]
        for name, code, price, chg in defaults:
            GarbagePrice.objects.create(name=name, code=code, price_per_kg=price, change_pct=chg)


def route_by_role(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    if profile.role == 'COLLECTOR':
        return redirect('collector_dashboard')
    elif profile.role == 'RECYCLER':
        return redirect('recycler_dashboard')
    elif profile.role == 'ADMIN':
        return redirect('admin_dashboard')
    return redirect('household_dashboard')


def home_redirect(request):
    ensure_initial_prices()
    if request.user.is_authenticated:
        return route_by_role(request.user)
    return redirect('login_view')


def login_view(request):
    ensure_initial_prices()
    error = None

    if request.method == 'POST':
        action = request.POST.get('action', 'login').strip()
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        role = request.POST.get('role', 'HOUSEHOLD').strip()

        if not username or not password:
            error = 'Please enter both username and password.'
        elif action == 'register':
            existing_user = User.objects.filter(username__iexact=username).first()
            if existing_user:
                error = f'Username "{username}" already exists! Please login below.'
            else:
                user = User.objects.create_user(username=username, password=password)
                UserProfile.objects.create(user=user, role=role)
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                return route_by_role(user)
        else:
            existing_user = User.objects.filter(username__iexact=username).first()
            if existing_user and existing_user.check_password(password):
                profile, _ = UserProfile.objects.get_or_create(user=existing_user)
                if role in ['HOUSEHOLD', 'COLLECTOR', 'RECYCLER', 'ADMIN']:
                    profile.role = role
                    profile.save()
                login(request, existing_user, backend='django.contrib.auth.backends.ModelBackend')
                return route_by_role(existing_user)
            else:
                error = 'Invalid username or password!'

    return render(request, 'core/login.html', {
        'error': error,
        'prices': GarbagePrice.objects.all(),
    })


def logout_view(request):
    logout(request)
    return redirect('login_view')


@login_required
def household_dashboard(request):
    ensure_initial_prices()
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        g_id = request.POST.get('garbage_id')
        est_kg = float(request.POST.get('estimated_weight_kg', 1.0))
        address = request.POST.get('address', '').strip()
        g_type = get_object_or_404(GarbagePrice, id=g_id)
        est_payout = round(est_kg * g_type.price_per_kg, 2)

        CollectionOrder.objects.create(
            household=request.user,
            garbage_type=g_type,
            address=address,
            estimated_weight_kg=est_kg,
            household_payout=est_payout,
            status='PENDING',
        )
        return redirect('household_dashboard')

    my_orders = CollectionOrder.objects.filter(household=request.user).order_by('-created_at')
    return render(request, 'core/household.html', {
        'profile': profile,
        'prices': GarbagePrice.objects.all(),
        'orders': my_orders,
        'latest_order': my_orders.first(),
        'trees_planted': round(profile.co2_saved_kg / 15.0, 1),
    })


@login_required
def collector_dashboard(request):
    ensure_initial_prices()
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'toggle_online':
            profile.is_online = not profile.is_online
            profile.save()

        elif action == 'accept_order':
            order = get_object_or_404(CollectionOrder, id=request.POST.get('order_id'))
            order.collector = request.user
            order.status = 'ACCEPTED'
            order.save()

        elif action == 'weigh_order':
            order = get_object_or_404(CollectionOrder, id=request.POST.get('order_id'))
            actual_kg = float(request.POST.get('actual_weight_kg', order.estimated_weight_kg))
            payout = round(actual_kg * order.garbage_type.price_per_kg, 2)
            rider_cut = round(payout * 0.20, 2)

            order.actual_weight_kg = actual_kg
            order.household_payout = payout
            order.collector_earning = rider_cut
            order.status = 'WEIGHED'
            order.save()

            hh_profile, _ = UserProfile.objects.get_or_create(user=order.household)
            hh_profile.wallet_balance = round(hh_profile.wallet_balance + payout, 2)
            hh_profile.co2_saved_kg = round(hh_profile.co2_saved_kg + (actual_kg * 2.1), 1)
            hh_profile.save()

            profile.wallet_balance = round(profile.wallet_balance + rider_cut, 2)
            profile.save()

        return redirect('collector_dashboard')

    available_orders = CollectionOrder.objects.filter(status='PENDING').order_by('-created_at')
    my_active_orders = CollectionOrder.objects.filter(collector=request.user).exclude(status='PENDING').order_by('-created_at')

    return render(request, 'core/collector.html', {
        'profile': profile,
        'prices': GarbagePrice.objects.all(),
        'available_orders': available_orders,
        'my_active_orders': my_active_orders,
    })


@login_required
def recycler_dashboard(request):
    ensure_initial_prices()
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create_demand':
            g_type = get_object_or_404(GarbagePrice, id=request.POST.get('garbage_id'))
            RecyclerDemand.objects.create(
                recycler=request.user,
                garbage_type=g_type,
                needed_kg=float(request.POST.get('needed_kg')),
                offered_bonus_per_kg=float(request.POST.get('bonus_price')),
            )

        elif action == 'receive_order':
            order = get_object_or_404(CollectionOrder, id=request.POST.get('order_id'))
            order.status = 'RECYCLED'
            order.save()

        elif action == 'sell_product':
            prod = RecycledProduct.objects.create(
                recycler=request.user,
                product_name=request.POST.get('product_name').strip(),
                quantity_kg=float(request.POST.get('quantity_kg')),
                price_per_kg=float(request.POST.get('price_per_kg')),
                manufacturer_buyer=request.POST.get('manufacturer_buyer').strip(),
                is_sold=True,
            )
            profile.wallet_balance = round(profile.wallet_balance + prod.total_price, 2)
            profile.save()

        return redirect('recycler_dashboard')

    incoming_orders = CollectionOrder.objects.filter(status__in=['WEIGHED', 'RECYCLED']).order_by('-created_at')
    demands = RecyclerDemand.objects.all().order_by('-created_at')
    products = RecycledProduct.objects.filter(recycler=request.user).order_by('-created_at')

    return render(request, 'core/recycler.html', {
        'profile': profile,
        'prices': GarbagePrice.objects.all(),
        'incoming_orders': incoming_orders,
        'demands': demands,
        'products': products,
    })


@login_required
def admin_dashboard(request):
    ensure_initial_prices()
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        action = request.POST.get('action', 'update_price')
        if action == 'add_garbage':
            name = request.POST.get('name').strip()
            code = request.POST.get('code').strip().upper()
            price = float(request.POST.get('price_per_kg'))
            GarbagePrice.objects.create(name=name, code=code, price_per_kg=price, change_pct=2.0)
        else:
            g_item = get_object_or_404(GarbagePrice, id=request.POST.get('garbage_id'))
            new_price = float(request.POST.get('new_price', g_item.price_per_kg))
            diff_pct = round(((new_price - g_item.price_per_kg) / max(1.0, g_item.price_per_kg)) * 100.0, 1)
            g_item.price_per_kg = new_price
            g_item.change_pct = diff_pct if diff_pct != 0 else 2.5
            g_item.save()
        return redirect('admin_dashboard')

    all_profiles = UserProfile.objects.select_related('user').all()
    all_orders = CollectionOrder.objects.all().order_by('-created_at')
    total_kg = sum((o.actual_weight_kg or o.estimated_weight_kg) for o in all_orders)
    total_payouts = sum(o.household_payout for o in all_orders)

    return render(request, 'core/admin_panel.html', {
        'profile': profile,
        'prices': GarbagePrice.objects.all(),
        'all_profiles': all_profiles,
        'all_orders': all_orders,
        'total_users': User.objects.count(),
        'total_orders': all_orders.count(),
        'total_kg': round(total_kg, 1),
        'total_payouts': round(total_payouts, 2),
    })


def api_ai_forecast(request):
    """Real-time API endpoint for AI 7-Day Scrap Price Forecaster."""
    ensure_initial_prices()
    garbage_id = request.GET.get('garbage_id')
    try:
        weight_kg = float(request.GET.get('weight_kg', 5.0))
        if weight_kg <= 0:
            weight_kg = 5.0
    except (ValueError, TypeError):
        weight_kg = 5.0

    result = forecast_garbage_price(garbage_id=garbage_id, weight_kg=weight_kg)
    return JsonResponse(result)


def api_live_ticker(request):
    ensure_initial_prices()
    items = list(GarbagePrice.objects.all())
    if items and random.random() < 0.75:
        pick = random.choice(items)
        delta = random.choice([-0.5, -0.25, +0.25, +0.5])
        pick.price_per_kg = round(max(5.0, pick.price_per_kg + delta), 2)
        pick.change_pct = round(pick.change_pct + (delta * 0.4), 1)
        pick.save()

    data = [
        {
            'id': p.id,
            'name': p.name,
            'code': p.code,
            'price': round(p.price_per_kg, 2),
            'change': round(p.change_pct, 1),
        }
        for p in GarbagePrice.objects.all().order_by('id')
    ]
    return JsonResponse({'prices': data})