import shutil
import xml.etree.ElementTree as ET
import os
import math
import re

# Global variable for placeholder name
PLACEHOLDER = "PLACEHOLDER"


def parse_config(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()
    
    waypoints = root.find('waypoints')
    ids = waypoints.find('id').text.split(',')
    x_coords = list(map(float, waypoints.find('x').text.split(',')))
    y_coords = list(map(float, waypoints.find('y').text.split(',')))
    z_coords = list(map(float, waypoints.find('z').text.split(',')))
    out_connections = [conn.split(',') for conn in waypoints.find('out').text.split(';')]
    incoming_connections = [conn.split(',') for conn in waypoints.find('incoming').text.split(';')]
    flags = list(map(int, waypoints.find('flags').text.split(',')))

    return ids, x_coords, y_coords, z_coords, out_connections, incoming_connections, flags

def generate_beam(id, x, y, z, node_id):
    return f'<Shape name="beam" translation="{x} {y} {z}" scale="0.1 2 0.1" shapeId="3" clipDistance="300" nodeId="{node_id}" castsShadows="false" receiveShadows="false" distanceBlending="false" materialIds="761"/>'

def calculate_line_properties(x1, y1, z1, x2, y2, z2):
    center_x = floatn((x1 + x2) / 2)
    center_y = floatn((y1 + y2) / 2)
    center_z = floatn((z1 + z2) / 2)
    length = floatn(((x2 - x1)**2 + (z2 - z1)**2)**0.5)
    
    rotation_y = floatn(-math.degrees(math.atan2(z2 - z1, x2 - x1)))
    return center_x, center_y, center_z, length, rotation_y

def generate_line(name, x, y, z, length, rotation_y, node_id, material_id):
    arrow_shapes = ""
    if name in ["green", "yellow"]:
        arrow_shapes = (
            f'<Shape name="{name}ArrowR" translation="0.032 0 0.0315634" rotation="45 0 90" scale="1 0.1 1" shapeId="4" clipDistance="300" nodeId="{node_id + 1}" castsShadows="false" receiveShadows="false" distanceBlending="false" materialIds="{material_id}"/>'
            f'<Shape name="{name}ArrowL" translation="0.032 0 -0.032" rotation="-45 0 90" scale="1 0.1 1" shapeId="4" clipDistance="300" nodeId="{node_id + 2}" castsShadows="false" receiveShadows="false" distanceBlending="false" materialIds="{material_id}"/>'
        )
        node_id += 2
    elif name == "cyan":
        arrow_shapes = (
            f'<Shape name="{name}ArrowR" translation="-0.032 0 0.0315634" rotation="-45 0 90" scale="1 0.1 1" shapeId="4" clipDistance="300" nodeId="{node_id + 1}" castsShadows="false" receiveShadows="false" distanceBlending="false" materialIds="{material_id}"/>'
            f'<Shape name="{name}ArrowL" translation="-0.032 0 -0.032" rotation="45 0 90" scale="1 0.1 1" shapeId="4" clipDistance="300" nodeId="{node_id + 2}" castsShadows="false" receiveShadows="false" distanceBlending="false" materialIds="{material_id}"/>'
        )
        node_id += 2

    return (
        f'<TransformGroup name="{name}Line" translation="{x} {y} {z}" rotation="0 {rotation_y} 0" nodeId="{node_id}">'
        f'<Shape name="{name}Line" rotation="180 0 90" scale="1 {length} 1" shapeId="4" clipDistance="300" nodeId="{node_id}" castsShadows="false" receiveShadows="false" distanceBlending="false" materialIds="{material_id}"/>'
        f'{arrow_shapes}'
        f'</TransformGroup>'
    )

def traverse_tree_find_path(root, target):
    for transform_group in root.findall('TransformGroup'):
        if transform_group.get('name') == 'generated':
            return transform_group
        else:
            result = traverse_tree_find_path(transform_group, target)
            if result:
                return result
    return None

def copy_i3d_structure(input_file, output_file, beams_content, lines_content, config_name):
    tree = ET.parse(input_file)
    root = tree.getroot()

    shapes_elem = root.find('Shapes')
    if shapes_elem is not None and 'externalShapesFile' in shapes_elem.attrib:
        shapes_elem.set('externalShapesFile', f"{config_name}.i3d.shapes")

    scene = root.find('Scene')
    # generated_group = None

    generated_group = traverse_tree_find_path(scene, 'generated')

    # for transform_group in scene.findall('TransformGroup'):
    #     if transform_group.get('name') == 'generated':
    #         generated_group = transform_group
    #         break

    if generated_group is not None:
        for child in generated_group.findall('TransformGroup'):
            if child.get('name') in ['beams', 'lines']:
                generated_group.remove(child)

        beams_group = ET.SubElement(generated_group, 'TransformGroup', name='beams', nodeId='974')
        for beam in beams_content:
            beams_group.append(ET.fromstring(beam))

        lines_group = ET.SubElement(generated_group, 'TransformGroup', name='lines', translation='0.0 0.9 0.0', nodeId='975')
        for line in lines_content:
            lines_group.append(ET.fromstring(line))

    tree.write(output_file, encoding='iso-8859-1', xml_declaration=True)

def copy_and_modify_xml_structure(config_file, template_xml, output_xml, config_name):
    tree = ET.parse(template_xml)
    root = tree.getroot()

    for elem in root.iter():
        if elem.text and PLACEHOLDER in elem.text:
            elem.text = elem.text.replace(PLACEHOLDER, config_name)

    config_tree = ET.parse(config_file)
    config_root = config_tree.getroot()
    waypoints = config_root.find('waypoints')

    autodrive_section = root.find('AutoDrive')
    if autodrive_section is not None:
        for child in autodrive_section.findall('waypoints'):
            autodrive_section.remove(child)

        autodrive_section.append(waypoints)

    tree.write(output_xml, encoding='utf-8', xml_declaration=True)

def update_mod_desc_icon_name(mod_desc_path, config_name):
    tree = ET.parse(mod_desc_path)
    root = tree.getroot()

    # Update <iconFilename> section
    icon_filename_elem = root.find('iconFilename')
    if icon_filename_elem is not None and PLACEHOLDER in icon_filename_elem.text:
        icon_filename_elem.text = icon_filename_elem.text.replace(PLACEHOLDER, config_name)

    tree.write(mod_desc_path, encoding='utf-8', xml_declaration=True)

def update_mod_desc(mod_desc_path, config_name):
    tree = ET.parse(mod_desc_path)
    root = tree.getroot()

    # for elem in root.iter():
    #     if elem.text and PLACEHOLDER in elem.text:
    #         elem.text = elem.text.replace(PLACEHOLDER, config_name)

    # Update <l10n> section
    l10n_section = root.find('l10n')
    if l10n_section is not None:
        name_elem = ET.SubElement(l10n_section, 'text', {'name': f"storeItem_{config_name}"})
        clean_name = re.sub(r'\W+', ' ', config_name)  # Remove non-word characters
        ET.SubElement(name_elem, 'en').text = clean_name

    # Update <storeItems> section
    store_items_section = root.find('storeItems')
    if store_items_section is not None:
        ET.SubElement(store_items_section, 'storeItem', {'xmlFilename': f"{config_name}.xml"})


    tree.write(mod_desc_path, encoding='utf-8', xml_declaration=True)

def generate_i3d_file(config_file, input_i3d, output_i3d, config_name):
    ids, x_coords, y_coords, z_coords, out_connections, incoming_connections, flags = parse_config(config_file)
    
    beams = []
    lines = []
    node_id_counter = 1000
    
    # for i, id in enumerate(ids):
    #     beams.append(generate_beam(id, x_coords[i], y_coords[i], z_coords[i], node_id_counter))
    #     node_id_counter += 1
    
    for i, id in enumerate(ids):
        beams.append(generate_beam(id, x_coords[i], y_coords[i], z_coords[i], node_id_counter))

        for out_id in out_connections[i]:
            if out_id == "-1":
                continue
            out_index = ids.index(out_id)
            center_x, center_y, center_z, length, rotation_y = calculate_line_properties(
                x_coords[i], y_coords[i], z_coords[i], x_coords[out_index], y_coords[out_index], z_coords[out_index]
            )
            
            if id in incoming_connections[out_index] and out_id in incoming_connections[i]:
                line_color = "blue" if flags[i] == 0 else "brown"
                material_id = "1066" if flags[i] == 0 else "1074"
            elif id not in incoming_connections[out_index]:
                line_color = "cyan"
                material_id = "1083"
            else:
                line_color = "green" if flags[i] == 0 else "yellow"
                material_id = "585" if flags[i] == 0 else "965"
            
            lines.append(generate_line(line_color, center_x, center_y, center_z, length, rotation_y, node_id_counter, material_id))
            node_id_counter += 1
    
    copy_i3d_structure(input_i3d, output_i3d, beams, lines, config_name)

def floatn(value):
    return "{:.2f}".format(value)

def main():
    cwd = os.getcwd()
    config_folder = 'configs'
    input_i3d = os.path.join(cwd, 'placeholders', 'placeholder.i3d')
    shapes_file = os.path.join(cwd, 'placeholders', 'placeholder.i3d.shapes')
    template_xml = os.path.join(cwd, 'placeholders', 'placeholder.xml')
    mod_desc_file = os.path.join(cwd, 'placeholders', 'modDesc.xml')
    mod_folder = 'FS25_autodrive_placeables'

    os.makedirs(mod_folder, exist_ok=True)

    # Copy modDesc.xml to mod folder
    mod_desc_path = os.path.join(cwd, mod_folder, os.path.split(mod_desc_file)[1])
    shutil.copy(mod_desc_file, mod_desc_path)
    update_mod_desc_icon_name(mod_desc_path, mod_folder)

    for config_file in os.listdir(config_folder):
        if config_file.endswith('.xml'):
            config_path = os.path.join(config_folder, config_file)
            base_name = os.path.splitext(config_file)[0]

            # Generate I3D file
            output_i3d_file = os.path.join(mod_folder, f"{base_name}.i3d")
            generate_i3d_file(config_path, input_i3d, output_i3d_file, base_name)

            # Copy shapes file
            shapes_output = os.path.join(mod_folder, f"{base_name}.i3d.shapes")
            if os.path.exists(shapes_file):
                shutil.copy(shapes_file, shapes_output)
            else:
                print(f"Warning: {shapes_file} does not exist and cannot be copied.")
            
            # Generate XML file
            output_xml_file = os.path.join(mod_folder, f"{base_name}.xml")
            copy_and_modify_xml_structure(config_path, template_xml, output_xml_file, base_name)
            
            # Update modDesc.xml
            update_mod_desc(mod_desc_path, base_name)

if __name__ == '__main__':
    main()