from PIL import Image, ImageDraw, ImageFont

W, H = 900, 620
SANS_B = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
SANS_R = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"

def f(path, size):
    try: return ImageFont.truetype(path, size)
    except: return ImageFont.load_default()

img = Image.new("RGB", (W, H), (13, 17, 23))  # GitHub dark bg
d = ImageDraw.Draw(img)

# Title bar
d.rectangle([0, 0, W, 50], fill=(22, 27, 34))
d.text((20, 14), "github.com/settings/installations", font=f(SANS_R, 16), fill=(139, 148, 158))

# Step labels on left
steps = [
    (1, "Open this URL in your browser:", "#58a6ff"),
    (2, 'Find "Claude" app → click Configure', "#3fb950"),
    (3, 'Set Contents → Read and Write', "#f0883e"),
    (4, "Click Save — done!", "#3fb950"),
]

y = 70
for num, text, color in steps:
    # Circle
    d.ellipse([20, y, 54, y+34], fill=color)
    d.text((33 if num < 10 else 28, y+6), str(num), font=f(SANS_B, 16), fill=(13,17,23))
    d.text((70, y+7), text, font=f(SANS_B, 16), fill=(230, 237, 243))
    y += 55

# URL box (step 1)
d.rectangle([70, 92, W-20, 120], fill=(22, 27, 34), outline=(48, 54, 61), width=2)
d.text((84, 98), "https://github.com/settings/installations", font=f(SANS_B, 15), fill="#58a6ff")

# Mock GitHub installations page
y_mock = 310
d.rectangle([70, y_mock, W-20, H-20], fill=(22, 27, 34), outline=(48, 54, 61), width=1)
d.text((90, y_mock+14), "Installed GitHub Apps", font=f(SANS_B, 15), fill=(230,237,243))
d.line([(70, y_mock+40), (W-20, y_mock+40)], fill=(48,54,61), width=1)

# App row
d.rectangle([80, y_mock+50, W-30, y_mock+100], fill=(30,37,46), outline=(48,54,61), width=1)
# App icon (purple circle)
d.ellipse([96, y_mock+62, 126, y_mock+90], fill=(139,92,246))
d.text((104, y_mock+67), "C", font=f(SANS_B, 18), fill=(255,255,255))
d.text((136, y_mock+60), "Claude", font=f(SANS_B, 14), fill=(230,237,243))
d.text((136, y_mock+78), "Installed on: rurytiuiuiopi/zynara", font=f(SANS_R, 12), fill=(139,148,158))

# Configure button with arrow
d.rectangle([W-130, y_mock+62, W-40, y_mock+88], fill=(33,139,116), outline=(33,139,116))
d.text((W-120, y_mock+67), "Configure", font=f(SANS_B, 13), fill=(255,255,255))

# Arrow pointing to Configure
d.polygon([
    (W-160, y_mock+68), (W-138, y_mock+75), (W-160, y_mock+82)
], fill="#f0883e")
d.text((W-260, y_mock+68), "← Click this", font=f(SANS_B, 13), fill="#f0883e")

# After clicking - permissions section
d.text((90, y_mock+115), "After clicking Configure, scroll down to:", font=f(SANS_R, 13), fill=(139,148,158))

# Permissions box
d.rectangle([80, y_mock+138, W-30, y_mock+195], fill=(30,37,46), outline=(48,54,61), width=1)
d.text((96, y_mock+148), "Repository permissions", font=f(SANS_B, 13), fill=(230,237,243))
d.line([(80, y_mock+168), (W-30, y_mock+168)], fill=(48,54,61), width=1)
d.text((96, y_mock+176), "Contents:", font=f(SANS_R, 13), fill=(230,237,243))

# Dropdown showing Read and write
d.rectangle([W-240, y_mock+172, W-40, y_mock+194], fill=(13,17,23), outline=(48,54,61), width=1)
d.text((W-230, y_mock+176), "Read and write  ▾", font=f(SANS_B, 12), fill="#3fb950")

# Arrow to dropdown
d.polygon([
    (W-270, y_mock+176), (W-248, y_mock+183), (W-270, y_mock+190)
], fill="#f0883e")
d.text((W-420, y_mock+176), "← Change to this", font=f(SANS_B, 12), fill="#f0883e")

img.save("/home/user/zynara/static/shatta/github_guide.png")
print("Guide saved")
