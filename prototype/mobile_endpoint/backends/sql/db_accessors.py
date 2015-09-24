import json
from sqlalchemy import Text
from sqlalchemy.sql import text, bindparam
from mobile_endpoint.models import CaseData, db, FormData


def create_or_update_case(case):
    sel = text("""
        select create_or_update_case(
            :domain, :case_id, :closed, :owner_id, :server_modified_on, :version, :case_json, :attachments, :is_new
        )
    """)
    params = {'case_id': case.id, 'version': 0, 'attachments': None, 'is_new': not hasattr(case, '_self')}
    case_json = case.to_json()
    case_json.pop('indices')  # drop indices since they are stored separately
    for att in ['domain', 'owner_id', 'closed', 'server_modified_on']:
        params[att] = getattr(case, att)
        case_json.pop(att)
    params['case_json'] = json.dumps(case_json)

    sel = sel.bindparams(**params)
    db.session.execute(sel)


def get_case_by_id(domain, case_id):
    sel = text("""
        select id, domain, closed, owner_id, server_modified_on, version, case_json, attachments
        from get_case_by_id(:domain, :case_id)
    """)
    sel = sel.bindparams(domain=domain, case_id=case_id)
    res = db.session.execute(sel)
    rows = list(res)
    if rows:
        return _row_to_case(rows[0])


def create_form(form):
    sel = text("""
        select insert_form(
            :domain, :form_id, :received_on, :user_id, :md5, :synclog_id, :attachments
        )
    """)
    sel = sel.bindparams(
        domain=form.domain,
        form_id=form.id,
        received_on=form.received_on,
        user_id=form.metadata.userID,
        md5=str(form._md5),
        synclog_id=form.last_sync_token,
        attachments=None
    )
    db.session.execute(sel)


def get_form_by_id(domain, form_id):
    sel = text("select * from get_form_by_id(:domain, :form_id)")
    sel = sel.bindparams(domain=domain, form_id=form_id)
    res = db.session.execute(sel)
    rows = list(res)
    if rows:
        kwargs = dict(rows[0].items())
        return FormData(**kwargs)


def create_or_update_case_indices(case):
    if case.indices:
        index_template = "ROW(:identifier{i}, cast(:referenced_id{i} as uuid), :referenced_type{i}, :is_new{i})::case_index_row"
        rows = []
        params = {}
        for i, index in enumerate(case.indices):
            params['is_new{}'.format(i)] = not hasattr(index, '_self')
            for att in ['identifier', 'referenced_type', 'referenced_id', 'referenced_type']:
                params['{}{}'.format(att, i)] = getattr(index, att)
            rows.append(index_template.format(i=i))

        sel = text("""
            select create_or_update_case_indices(
                :domain, :case_id, ARRAY[{}]
            )
        """.format(','.join(rows)))
        sel = sel.bindparams(
            domain=case.domain,
            case_id=case.id,
            **params
        )
        db.session.execute(sel)


def get_cases(domain, case_ids):
    params, names = _get_array_params('case_id', case_ids)
    sel = text("select * from get_cases(:domain, ARRAY[{}])".format(names))
    sel = sel.bindparams(domain=domain, **params)
    res = db.session.execute(sel)
    return [_row_to_case(row) for row in res]


def get_open_case_ids(domain, owner_id):
    sel = text("select * from get_open_case_ids(:domain, :owner_id)")
    sel = sel.bindparams(domain=domain, owner_id=owner_id)
    res = db.session.execute(sel)
    return [row[0] for row in res]


def get_reverse_indexed_cases(domain, case_ids):
    params, names = _get_array_params('case_id', case_ids)
    sel = text("select * from get_reverse_index_case_ids(:domain, ARRAY[{}]::uuid[])".format(names))
    sel = sel.bindparams(
        bindparam('domain', domain, type_=Text()),
        **params
    )
    res = db.session.execute(sel)
    indexed_case_ids = [row[0] for row in res]
    if indexed_case_ids:
        return get_cases(domain, indexed_case_ids)
    else:
        return []


def _row_to_case(row):
    kwargs = dict(row.items())
    return CaseData(**kwargs)


def _get_array_params(slug, args):
    params = {'{}{}'.format(slug, i): arg for i, arg in enumerate(args)}
    names = [':{}'.format(name) for name in params.keys()]
    return params, ','.join(names)
