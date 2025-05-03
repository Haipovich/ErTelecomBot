from . import common, support, jobs, activities, applications, profile

routers_list = [
    profile.router,
    jobs.router,
    activities.router,
    applications.router,
    support.router,
    common.router,
]