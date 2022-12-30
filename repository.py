from typing import Any, Callable


class SpecialMethodNotImplementedError(Exception):
    ...


class BaseRepository:
    """
    Repository object is a middle layer to use Django ORM API on different
    parts of the project. Purpose of this approach is to minimize complexity
    of hidden (magical) approach of ORM specific objects like managers or querysets.
    You can see all annotation and filter methods at once and easily extend
    the layer without concern of breaking other parts of the code.

    Concept:
        -   When you initialize the Repository object, you get default
            `self.model.object.all()` qs as `self.instance_list`.
            All methods should filter or fetch data directly from instance_list.
            Also, you have an option to add default `annotation` and `filter` methods.

    Methods:
        *   add_annotations - This method helps you to extend annotated fields
            on the `instance_list` objects. You can create `annotate_<your_annotation_field_name>`
            methods inside your repository object to call them with `add_annotations` method.

        *   add_filters - Like previous method, this method helps you to add default filters
            in your `instance_list`. You can create filter methods with methods named
            like `filter_<your_filter_name>`.

        *   extend - Sometimes you'll need to extend the capability of previously called
            repository object. `extend` method helps you to add new annotations
            and filters on your `instance_list`.

        *   clean - This method cleans current annotation and filter state of the repository.
            This is very helpful to use previously called repository object in a different use case.

        *   state - State dictionary shows currently used annotation and filter methods in
            your repository. Usefull for debugging purposes.

        *   context - In some cases, you'll need to use some context-related data in your
            repository methods. This is something like DRF serializers context.

        *   `get_filters` and `get_annotations` methods are usefull to see the list of the
            implemented filters and annotations in your repo object.

    Examples:
        > my_repo = MyModelRepository()

        >> my_repo.add_annotations(["my_annotated_field1", "my_annotated_field2"])
        In this case, you should have `my_repo.annotate_my_annotated_field1()` and
        `my_repo.annotate_my_annotated_field2()` methods defined in your `my_repo` object.

        >> my_repo.add_filters(["is_active", "is_minted"])
        In this case, you should have `my_repo.filter_is_active()` and
        `my_repo.filter_is_minted()` methods defined in your `my_repo` object.

        >> my_repo.extend(
            annotations=["my_annotated_field3"],
            filters=["is_owned"],
            context={"user": user}
        )
        >> print(my_repo.state)
        >> {
            "annotations" : [
                "my_annotated_field1",
                "my_annotated_field2",
                "my_annotated_field1"
            ],
            "filters: ["is_active", "is_minted", "is_owned"]
          }
        >> print(my_repo.context)
        >> {"user" : User}
        extend method is super usefull when you want to add new annotation
        and filters or context variables after initialized.
    """

    model: object

    _special_methods: dict[str, str] = {"annotations": "annotate", "filters": "filter"}

    def __init__(self):
        self.__instance_list = self.model.objects
        self.__context = {}
        self.__state = {"annotations": [], "filters": []}

    def get_annotations(self) -> list[str]:
        return [m for m in dir(self) if f'{self._special_methods["annotations"]}_' in m]

    @property
    def state(self):
        return self.__state

    def get_filters(self) -> list[str]:
        return [m for m in dir(self) if f'{self._special_methods["filters"]}_' in m]

    def filter(self, **kwargs) -> list[object]:
        return self.instance_list.filter(**kwargs)

    def get_all(self) -> list[object]:
        return self.instance_list.all()

    @property
    def instance_list(self):
        return self.__instance_list

    @instance_list.setter
    def instance_list(self, list: list[object]):
        self.__instance_list = list

    @property
    def context(self):
        return self.__context

    @context.setter
    def context(self, context: dict[str, Any]):
        self.__context = context

    def __add_type(self, type: str, k: str) -> None:
        if hasattr(self, f"{self._special_methods[type]}_{k.lower()}"):
            method = getattr(self, f"{self._special_methods[type]}_{k.lower()}")
            self.instance_list = method()
            self.__state[type].append(k.lower())
        else:
            raise SpecialMethodNotImplementedError(
                f"{k} {type} method is not implemented."
            )

    def add_annotations(self, annotations: list[str]):
        """
        This method helps you to extend annotated fields on the `instance_list`
        objects. You can create `annotate_<your_annotation_field_name>` methods
        inside your repository object to call them view add_annotations method.
        """
        for k in annotations:
            self.__add_type("annotations", k)
        return self

    def add_filters(self, filters: list[str]):
        """
        This method helps you to add default filters in your `instance_list`.
        You can create filter methods with methods named like `filter_<your_filter_name>`.
        """
        for k in filters:
            self.__add_type("filters", k)
        return self

    def clean(self) -> list[Callable]:
        """This method cleans current annotation and filter state of the repository."""
        self.instance_list = self.model.objects
        self.state.update({"annotations": [], "filters": []})
        return self

    def extend(self, **kwds):
        """
        This method helps you to add new annotations and filters on your `instance_list`.
        """
        if "context" in kwds.keys():
            self.context = kwds["context"]

        if "annotations" in kwds.keys():
            for k in kwds["annotations"]:
                self.__add_type("annotations", k)

        if "filters" in kwds.keys():
            for k in kwds["filters"]:
                self.__add_type("filters", k)

        return self

