# Delivery note: tasting-programme checklist extract

Prepared by the compliance team. Dates are ISO `YYYY-MM-DD`. The extract was taken
on 2026-05-04, before the season opens.

`checklist_mentions.csv`: the positions recorded in the checklist at the extract date.
Columns: `mention_ref`, `item_id`, `checklist_section`, `event_date`, `district`,
`subject`, `draft_position`, `cited_section`, `context_id`.

`district_control_totals.csv`: what each district section reports it contains.
Columns: `district`, `mentions_reported`, `items_reported`, `contexts_attached`.

`citation_manifest.csv`: the sections the checklist cites, as recorded by the team.
Columns: `cited_section`, `record_on_file`, `batch`, `received_on`.

`tasting_context.csv`: the facts recorded for each position by the events team.
Columns: `context_id`, `every_server_is_holder_employee`, `store_holds_own_permit`, `tasting_open_to_public`, `event_inside_licensed_area`, `product_sold_at_event`, `brand_products_only`, `containers_sealed_on_arrival`, `inside_permitted_hours`.
