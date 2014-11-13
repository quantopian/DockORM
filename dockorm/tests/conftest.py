from ..container import Container
from pytest import fixture


@fixture
def busybox(request):
    bb = Container(
        image=u'busybox',
        name=u'busybox-dockorm-testing',
    )

    def clean():
        bb.purge(stop_first=False, remove_volumes=True)

    request.addfinalizer(clean)

    return bb
