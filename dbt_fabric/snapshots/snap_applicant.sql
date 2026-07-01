{% snapshot snap_applicant %}
{{
    config(
        target_schema='snapshots',
        unique_key='applicant_id',
        strategy='check',
        check_cols=['name_income_type', 'name_education_type', 'name_family_status', 'cnt_children'],
    )
}}
select * from {{ ref('int_applicant_attributes') }}
{% endsnapshot %}
