# Django Repository

Repository object is a middle layer to use Django ORM API on different
parts of the project. Purpose of this approach is to minimize complexity
of hidden (magical) approach of ORM specific objects like managers or querysets.
You can see all annotation and filter methods at once and easily extend
the layer without concern of breaking other parts of the code.

## Concept:
-   When you initialize the Repository object, you get default
    `self.model.objects` manager as `self.instance_list`.
    All methods should filter or fetch data directly from instance_list.
    Also, you have an option to add default `annotation` and `filter` methods.

## Methods:
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


## Examples:

```python
>> my_repo = MyModelRepository()

>> my_repo.add_annotations(["my_annotated_field1", "my_annotated_field2"])
# In this case, you should have `my_repo.annotate_my_annotated_field1()` and
# `my_repo.annotate_my_annotated_field2()` methods defined in your `my_repo` object.

>> my_repo.add_filters(["is_active", "is_minted"])
# In this case, you should have `my_repo.filter_is_active()` and
# `my_repo.filter_is_minted()` methods defined in your `my_repo` object.

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
    "filters" : ["is_active", "is_minted", "is_owned"]
    }
>> print(my_repo.context)
>> {"user" : User}
# `extend` method is super usefull when you want to add new annotation
# and filters or context variables after initialized.
```


## Implemented version example:

```python
from typing import Tuple, List
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import (
    BooleanField,
    IntegerField,
    Case,
    When,
    Count,
    Q,
    F,
    Sum,
    OuterRef,
    Exists,
)
from django.db.models.functions import Cast, Coalesce, JSONObject
from django.db.models.lookups import GreaterThan
from project.domain_object.models import DOMAINOBJ
from project.core.helpers import model_fields_dict
from project.core.choices import ApprovalState, TransactionState
from project.core.base import BaseRepository

__all__ = ["DOMAINOBJRepository"]

User = get_user_model()

class DOMAINOBJRepository(BaseRepository):
    model = DOMAINOBJ

    @transaction.atomic
    def create_with_related_obj(self, **kwargs) -> DOMAINOBJ:
        obj = DOMAINOBJ(title=kwargs.get("title")).save()
        related_obj = RelatedOBJ.objects.create(domain_obj=obj, value=10)
        return obj

    def filter_approved(self) -> List[DOMAINOBJ]:
        return self.instance_list.filter(approval_state=ApprovalState.APPROVED)

    def annotate_available_for_listing(self) -> List[DOMAINOBJ]:
        return self.instance_list.annotate(
            is_available_for_listing=Case(
                When(
                    Q(
                        GreaterThan(
                            Count(
                                "instantlistings",
                                filter=Q(
                                    instantlistings__status__in=(
                                        Listing.get_ongoing_status_values()
                                    )
                                ),
                            ),
                            0,
                        )
                    )
                    | Q(
                        GreaterThan(
                            Count(
                                "scheduledlistings",
                                filter=Q(
                                    scheduledlistings__status__in=(
                                        listingStatuses.get_ongoing_status_values()
                                    )
                                ),
                            ),
                            0,
                        )
                    )
                    & Q(standard=DOMAINOBJValueStandards.BRA_055.value),
                    then=False,
                ),
                default=Cast(True, output_field=BooleanField()),
                output_field=BooleanField(),
            )
        )

    def annotate_number_of_likes(self) -> List[DOMAINOBJ]:
        return self.instance_list.annotate(number_of_likes=Count("likes"))

    def annotate_is_liked(self):
        likes = self.model.objects.none()
        user = self.context.get("user", User)
        if user.is_authenticated:
            likes = self.model.objects.filter(
                likes__id__contains=user.id, pk=OuterRef("pk")
            )
        return self.instance_list.annotate(
            is_liked=Case(
                When(Exists(likes), then=True),
                default=Cast(False, output_field=BooleanField()),
                output_field=BooleanField(),
            ),
        )

    def get_by_id(self, id: int) -> DOMAINOBJ:
        return self.instance_list.get(id=id)

    def get_by_owner(self) -> List[DOMAINOBJ]:
        return self.instance_list.filter(owners__user=self.context.get("user", User))

    def show_available_items_for_listing(self, id: int) -> Tuple[int, int]:
        domain_object = self.get_by_id(id=id)
        return domain_object.available_items_for_listing
```
