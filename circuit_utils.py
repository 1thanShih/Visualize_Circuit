import math

GRID_SIZE = 20

def snap(value):
    """將座標吸附到網格上 (邏輯座標)"""
    return round(value / GRID_SIZE) * GRID_SIZE

def dist(p1, p2):
    """計算兩點距離"""
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def rotate_point(x, y, angle_deg):
    rad = math.radians(angle_deg)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)
    new_x = x * cos_a - y * sin_a
    new_y = x * sin_a + y * cos_a
    return new_x, new_y

def transform_coords(coords_list, x_offset, y_offset, rotation, mirror, scale=1.0):
    """
    將相對座標轉換為絕對座標，並支援縮放
    """
    transformed = []
    for (x, y) in coords_list:
        if mirror: x = -x
        x, y = rotate_point(x, y, rotation)
        
        screen_x = (x + x_offset) * scale
        screen_y = (y + y_offset) * scale
        
        transformed.append((screen_x, screen_y))
    return transformed

def is_point_on_segment(px, py, x1, y1, x2, y2, tolerance=5.0):
    """判斷點是否在線段上 (幾何運算使用邏輯座標)"""
    min_x, max_x = min(x1, x2) - tolerance, max(x1, x2) + tolerance
    min_y, max_y = min(y1, y2) - tolerance, max(y1, y2) + tolerance
    
    if not (min_x <= px <= max_x and min_y <= py <= max_y):
        return False

    line_len = dist((x1, y1), (x2, y2))
    if line_len == 0:
        return dist((px, py), (x1, y1)) < tolerance

    cross_product = abs((x2 - x1) * (y1 - py) - (x1 - px) * (y2 - y1))
    distance = cross_product / line_len

    return distance < tolerance

def get_closest_point_on_segment(px, py, x1, y1, x2, y2):
    lx = x2 - x1
    ly = y2 - y1
    if lx == 0 and ly == 0: return (x1, y1)
    u = ((px - x1) * lx + (py - y1) * ly) / (lx*lx + ly*ly)
    if u < 0: u = 0
    if u > 1: u = 1
    cx = x1 + u * lx
    cy = y1 + u * ly
    return (cx, cy)