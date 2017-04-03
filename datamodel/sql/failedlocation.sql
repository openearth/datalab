CREATE TABLE failed_location
(
  idlocation serial NOT NULL,
  thegeometry geometry NOT NULL,
  locationdescription character varying(255),
  orig_srid integer NOT NULL,
  username name NOT NULL DEFAULT "current_user"(),
  datetime timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT pk_failed_location PRIMARY KEY (idlocation),
  CONSTRAINT enforce_dims_thegeometry CHECK (st_ndims(thegeometry) = 2),
  CONSTRAINT enforce_geotype_thegeometry CHECK (geometrytype(thegeometry) = 'POINT'::text OR thegeometry IS NULL),
  CONSTRAINT enforce_srid_thegeometry CHECK (st_srid(thegeometry) = 4326)
)
WITH (
  OIDS=FALSE
);