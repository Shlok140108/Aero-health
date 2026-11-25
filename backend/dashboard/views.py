from django.shortcuts import render


def overview(request):
    return render(request, "aerohealth/overview.html")


def weather_page(request):
    return render(request, "aerohealth/weather.html")


def prediction(request):
    return render(request, "aerohealth/prediction.html")


def soon(title):
    """Placeholder for tabs whose design isn't built yet."""
    def view(request):
        return render(request, "aerohealth/soon.html", {"title": title})
    return view
