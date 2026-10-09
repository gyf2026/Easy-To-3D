"""Optional author-supplied hints, never a geometry operation interface."""
from .contracts import require, number
from .storage import confined

def validate(root,value,objects):
    require(isinstance(value,dict) and value.get('schema_version')=='1.0','Unknown parameter hint schema')
    require(isinstance(value.get('items'),list),'Parameter hint items required')
    seen=set()
    for item in value['items']:
        require(isinstance(item,dict),'Hint must be object')
        ident=item.get('id');require(isinstance(ident,str) and ident and ident not in seen,'Duplicate/missing hint ID');seen.add(ident)
        require(isinstance(item.get('purpose'),str) and bool(item['purpose'].strip()),'Hint purpose required')
        require(number(item.get('value')) or isinstance(item.get('value'),(str,bool)),'Hint value must be finite scalar')
        require(isinstance(item.get('object_ids'),list) and all(x in objects for x in item['object_ids']),'Hint refers to unknown object')
        source=confined(root,item['source_script']);require(source.is_file() and str(item['source_script']).startswith('scripts/'),'Hint source script missing')
        if 'source_line' in item:require(isinstance(item['source_line'],int) and item['source_line']>0,'Invalid source line')
    return value
