# api/public.py
#
# Endpoints públicos de la Anur-App API
# GET  /api/v1/species              → lista completa de especies
# GET  /api/v1/species/{id}         → detalle de una especie
# POST /api/v1/observations         → registrar observación

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from .species_data import SPECIES

router = APIRouter()


# ── Helpers ────────────────────────────────────────────────────

def _filter_species(
    species_list: list,
    categoria: Optional[str] = None,
    subcategoria: Optional[str] = None,
    endemica: Optional[bool] = None,
    venenosa: Optional[bool] = None,
    nocturna: Optional[bool] = None,
    region: Optional[str] = None,
    habitat: Optional[str] = None,
    estado_iucn: Optional[str] = None,
    q: Optional[str] = None,
) -> list:
    result = species_list
    if categoria:
        result = [s for s in result if s["categoria"] == categoria]
    if subcategoria:
        result = [s for s in result if s["subcategoria"] == subcategoria]
    if endemica is not None:
        result = [s for s in result if s["endemica_cr"] == endemica]
    if venenosa is not None:
        result = [s for s in result if s["venenosa"] == venenosa]
    if nocturna is not None:
        result = [s for s in result if s["nocturna"] == nocturna]
    if region:
        result = [
            s for s in result
            if region in s["regiones_cr"] or "Nacional" in s["regiones_cr"]
        ]
    if habitat:
        result = [s for s in result if habitat in s["habitats"]]
    if estado_iucn:
        result = [s for s in result if s["estado_iucn"] == estado_iucn]
    if q:
        q_lower = q.lower()
        result = [
            s for s in result
            if q_lower in s["nombre_comun_es"].lower()
            or q_lower in s["nombre_comun_en"].lower()
            or q_lower in s["nombre_cientifico"].lower()
            or any(q_lower in tag for tag in s["tags"])
        ]
    return result


# ── Rutas ──────────────────────────────────────────────────────

@router.get("/species")
async def get_species(
    categoria: Optional[str] = Query(None, description="'anfibio' o 'reptil'"),
    subcategoria: Optional[str] = Query(None),
    endemica: Optional[bool] = Query(None),
    venenosa: Optional[bool] = Query(None),
    nocturna: Optional[bool] = Query(None),
    region: Optional[str] = Query(None, description="ej: 'Caribe', 'Pacífico Norte'"),
    habitat: Optional[str] = Query(None, description="ej: 'bosque_humedo', 'rio'"),
    estado_iucn: Optional[str] = Query(None, description="LC | NT | VU | EN | CR | EX"),
    q: Optional[str] = Query(None, description="Búsqueda de texto libre"),
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """
    Devuelve la lista de especies con filtros opcionales.
    Todos los parámetros son opcionales y se pueden combinar.
    """
    filtered = _filter_species(
        SPECIES,
        categoria=categoria,
        subcategoria=subcategoria,
        endemica=endemica,
        venenosa=venenosa,
        nocturna=nocturna,
        region=region,
        habitat=habitat,
        estado_iucn=estado_iucn,
        q=q,
    )
    total = len(filtered)
    page = filtered[offset: offset + limit]
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "results": page,
    }


@router.get("/species/{species_id}")
async def get_species_by_id(species_id: str):
    """Devuelve el detalle completo de una especie por su ID."""
    species = next((s for s in SPECIES if s["id"] == species_id), None)
    if species is None:
        raise HTTPException(status_code=404, detail=f"Especie '{species_id}' no encontrada")
    return species


@router.get("/species/stats/summary")
async def get_stats():
    """Estadísticas generales de la base de datos."""
    return {
        "total": len(SPECIES),
        "anfibios": sum(1 for s in SPECIES if s["categoria"] == "anfibio"),
        "reptiles": sum(1 for s in SPECIES if s["categoria"] == "reptil"),
        "endemicas_cr": sum(1 for s in SPECIES if s["endemica_cr"]),
        "amenazadas": sum(1 for s in SPECIES if s["estado_iucn"] in ["VU", "EN", "CR"]),
        "extintas": sum(1 for s in SPECIES if s["estado_iucn"] == "EX"),
        "venenosas": sum(1 for s in SPECIES if s["venenosa"]),
        "por_categoria": {
            "rana": sum(1 for s in SPECIES if s["subcategoria"] == "rana"),
            "sapo": sum(1 for s in SPECIES if s["subcategoria"] == "sapo"),
            "salamandra": sum(1 for s in SPECIES if s["subcategoria"] == "salamandra"),
            "cecilia": sum(1 for s in SPECIES if s["subcategoria"] == "cecilia"),
            "serpiente": sum(1 for s in SPECIES if s["subcategoria"] == "serpiente"),
            "iguana": sum(1 for s in SPECIES if s["subcategoria"] == "iguana"),
            "lagartija": sum(1 for s in SPECIES if s["subcategoria"] == "lagartija"),
            "gecko": sum(1 for s in SPECIES if s["subcategoria"] == "gecko"),
            "cocodrilo": sum(1 for s in SPECIES if s["subcategoria"] == "cocodrilo"),
            "tortuga_marina": sum(1 for s in SPECIES if s["subcategoria"] == "tortuga_marina"),
            "tortuga_terrestre": sum(1 for s in SPECIES if s["subcategoria"] == "tortuga_terrestre"),
        }
    }


@router.post("/observations")
async def create_observation(data: dict):
    """
    Registra una observación de campo.
    Campos esperados:
      taxon_id, count, behavior, notes, event_date, lat, lng
    """
    required = ["taxon_id", "event_date", "lat", "lng"]
    missing = [f for f in required if f not in data]
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Campos requeridos faltantes: {', '.join(missing)}"
        )

    # Verificar que el taxon_id exista
    species = next((s for s in SPECIES if s["id"] == data["taxon_id"]), None)
    if species is None:
        raise HTTPException(
            status_code=404,
            detail=f"Especie con id '{data['taxon_id']}' no existe en la base de datos"
        )

    # TODO: Guardar en base de datos real
    return {
        "message": "Observación registrada exitosamente",
        "species_name": species["nombre_comun_es"],
        "scientific_name": species["nombre_cientifico"],
        "data": data,
    }
