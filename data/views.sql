
-- This SQL script creates a view that aggregates entity details along with their links
-- Update this if you add new link types or entity attributes
CREATE OR REPLACE VIEW vw_entity_details AS
SELECT 
    e.id,
    e.guild_id,
    e.name,
    e.owner_id,
    e.entity_type,
    e.system,
    e.avatar_url,
    e.access_type,
    (
        SELECT jsonb_agg(jsonb_build_object('id', child.id, 'name', child.name))
        FROM entity_links el
        JOIN entities child ON el.to_entity_id = child.id
        WHERE el.from_entity_id = e.id AND el.link_type = 'possesses'
    ) AS possessed_items,
    (
        SELECT jsonb_agg(jsonb_build_object('id', parent.id, 'name', parent.name))
        FROM entity_links el
        JOIN entities parent ON el.from_entity_id = parent.id
        WHERE el.to_entity_id = e.id AND el.link_type = 'possesses'
    ) AS possessed_by,
    (
        SELECT jsonb_agg(jsonb_build_object('id', child.id, 'name', child.name))
        FROM entity_links el
        JOIN entities child ON el.to_entity_id = child.id
        WHERE el.from_entity_id = e.id AND el.link_type = 'controls'
    ) AS controls,
    (
        SELECT jsonb_agg(jsonb_build_object('id', parent.id, 'name', parent.name))
        FROM entity_links el
        JOIN entities parent ON el.from_entity_id = parent.id
        WHERE el.to_entity_id = e.id AND el.link_type = 'controls'
    ) AS controlled_by
FROM entities e;

