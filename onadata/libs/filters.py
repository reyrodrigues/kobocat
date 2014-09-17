from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import six
from rest_framework import filters
from rest_framework.exceptions import ParseError

from onadata.apps.logger.models import XForm, Instance


class AnonDjangoObjectPermissionFilter(filters.DjangoObjectPermissionsFilter):
    def filter_queryset(self, request, queryset, view):
        """
        Anonymous user has no object permissions, return queryset as it is.
        """
        if request.user.is_anonymous():
            return queryset

        return super(AnonDjangoObjectPermissionFilter, self)\
            .filter_queryset(request, queryset, view)


class XFormOwnerFilter(filters.BaseFilterBackend):

    owner_prefix = 'user'

    def filter_queryset(self, request, queryset, view):
        owner = request.QUERY_PARAMS.get('owner')

        if owner:
            kwargs = {
                self.owner_prefix + '__username': owner
            }

            return queryset.filter(**kwargs)

        return queryset


class ProjectOwnerFilter(XFormOwnerFilter):
    owner_prefix = 'organization'


class AnonUserProjectFilter(filters.DjangoObjectPermissionsFilter):
    def filter_queryset(self, request, queryset, view):
        """
        Anonymous user has no object permissions, return queryset as it is.
        """
        user = request.user
        if user.is_anonymous():
            return queryset.filter(Q(shared=True))

        return super(AnonUserProjectFilter, self)\
            .filter_queryset(request, queryset, view)


class TagFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        # filter by tags if available.
        tags = request.QUERY_PARAMS.get('tags', None)

        if tags and isinstance(tags, six.string_types):
            tags = tags.split(',')
            return queryset.filter(tags__name__in=tags)

        return queryset


class XFormPermissionFilterMixin(object):
    def _xform_filter_queryset(self, request, queryset, view, keyword):
        """Use XForm permissions"""
        xform = request.QUERY_PARAMS.get('xform')
        if xform:
            try:
                int(xform)
            except ValueError:
                raise ParseError(
                    u"Invalid value for formid %s." % xform)
            xform = get_object_or_404(XForm, pk=xform)
            xform_qs = XForm.objects.filter(pk=xform.pk)
        else:
            xform_qs = XForm.objects.all()
        xforms = super(XFormPermissionFilterMixin, self).filter_queryset(
            request, xform_qs, view)
        kwarg = {"%s__in" % keyword: xforms}

        return queryset.filter(**kwarg)


class MetaDataFilter(XFormPermissionFilterMixin,
                     filters.DjangoObjectPermissionsFilter):
    def filter_queryset(self, request, queryset, view):
        return self._xform_filter_queryset(request, queryset, view, 'xform')


class AttachmentFilter(XFormPermissionFilterMixin,
                       filters.DjangoObjectPermissionsFilter):
    def filter_queryset(self, request, queryset, view):
        queryset = self._xform_filter_queryset(request, queryset, view,
                                               'instance__xform')
        instance_id = request.QUERY_PARAMS.get('instance')
        if instance_id:
            try:
                int(instance_id)
            except ValueError:
                raise ParseError(
                    u"Invalid value for instance %s." % instance_id)
            instance = get_object_or_404(Instance, pk=instance_id)
            queryset = queryset.filter(instance=instance)

        return queryset