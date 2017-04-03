CREATE OR REPLACE FUNCTION unique_location(geometry)
  RETURNS integer AS
$BODY$
--SELECT count(idlocation)::integer FROM location_point WHERE st_within(thegeometry, st_buffer($1, 8.1818181818181818181818181818182e-6)); --this is approx. 1 meter
SELECT count(idlocation)::integer FROM location_point WHERE st_dwithin(ST_GeographyFromText(st_asEWKT(thegeometry)),ST_GeographyFromText(st_asEWKT($1)),1)
$BODY$
  LANGUAGE sql IMMUTABLE
  COST 100;
ALTER FUNCTION unique_location(geometry)
  OWNER TO postgres;