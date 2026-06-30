import os
import io
import random
import colorsys
from datetime import datetime
from PIL import Image
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# ==================== CONFIGURATION ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set!")

# User sessions
user_sessions = {}

# ==================== COLOR FUNCTIONS ====================
def rgb_to_hex(r, g, b):
    """Convert RGB to HEX color code"""
    return f"#{r:02x}{g:02x}{b:02x}"

def hex_to_rgb(hex_color):
    """Convert HEX to RGB tuple"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def generate_random_color():
    """Generate a random color"""
    r = random.randint(0, 255)
    g = random.randint(0, 255)
    b = random.randint(0, 255)
    return r, g, b

def generate_palette(base_rgb=None, count=5):
    """Generate a color palette"""
    if not base_rgb:
        base_rgb = generate_random_color()
    
    palette = []
    hue, sat, val = colorsys.rgb_to_hsv(base_rgb[0]/255, base_rgb[1]/255, base_rgb[2]/255)
    
    for i in range(count):
        new_hue = hue + (i - count//2) * 0.06
        new_hue = new_hue % 1.0
        new_sat = min(1.0, sat * (0.7 + i * 0.1))
        new_val = min(1.0, val * (0.7 + i * 0.1))
        
        r, g, b = colorsys.hsv_to_rgb(new_hue, new_sat, new_val)
        r, g, b = int(r*255), int(g*255), int(b*255)
        palette.append((r, g, b))
    
    return palette

def generate_complementary(base_rgb):
    """Generate complementary color"""
    hue, sat, val = colorsys.rgb_to_hsv(base_rgb[0]/255, base_rgb[1]/255, base_rgb[2]/255)
    comp_hue = (hue + 0.5) % 1.0
    r, g, b = colorsys.hsv_to_rgb(comp_hue, sat, val)
    return int(r*255), int(g*255), int(b*255)

def generate_analogous(base_rgb, count=5):
    """Generate analogous colors"""
    colors = []
    hue, sat, val = colorsys.rgb_to_hsv(base_rgb[0]/255, base_rgb[1]/255, base_rgb[2]/255)
    for i in range(count):
        offset = (i - count//2) * 0.08
        new_hue = (hue + offset) % 1.0
        r, g, b = colorsys.hsv_to_rgb(new_hue, sat, val)
        r, g, b = int(r*255), int(g*255), int(b*255)
        colors.append((r, g, b))
    return colors

def generate_triad(base_rgb):
    """Generate triad colors"""
    colors = []
    hue, sat, val = colorsys.rgb_to_hsv(base_rgb[0]/255, base_rgb[1]/255, base_rgb[2]/255)
    for offset in [0, 0.333, 0.667]:
        new_hue = (hue + offset) % 1.0
        r, g, b = colorsys.hsv_to_rgb(new_hue, sat, val)
        r, g, b = int(r*255), int(g*255), int(b*255)
        colors.append((r, g, b))
    return colors

def generate_monochromatic(base_rgb, count=5):
    """Generate monochromatic colors"""
    colors = []
    hue, sat, val = colorsys.rgb_to_hsv(base_rgb[0]/255, base_rgb[1]/255, base_rgb[2]/255)
    for i in range(count):
        new_val = max(0.1, min(1.0, val * (0.3 + i * 0.2)))
        r, g, b = colorsys.hsv_to_rgb(hue, sat, new_val)
        r, g, b = int(r*255), int(g*255), int(b*255)
        colors.append((r, g, b))
    return colors

def generate_color_swatch(r, g, b):
    """Generate a visual color swatch representation"""
    hex_code = rgb_to_hex(r, g, b)
    return f"⬛ {hex_code}"

# ==================== KEYBOARD FUNCTIONS ====================
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("🎨 Generate Palette", callback_data="palette")],
        [InlineKeyboardButton("🎲 Random Color", callback_data="random")],
        [InlineKeyboardButton("🔀 Color Schemes", callback_data="schemes")],
        [InlineKeyboardButton("📋 Saved Colors", callback_data="saved")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_scheme_keyboard():
    keyboard = [
        [InlineKeyboardButton("🔁 Complementary", callback_data="scheme_complementary")],
        [InlineKeyboardButton("🌈 Analogous", callback_data="scheme_analogous")],
        [InlineKeyboardButton("🔺 Triad", callback_data="scheme_triad")],
        [InlineKeyboardButton("📐 Monochromatic", callback_data="scheme_mono")],
        [InlineKeyboardButton("🎨 All Schemes", callback_data="scheme_all")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_palette_keyboard():
    keyboard = [
        [InlineKeyboardButton("🔄 New Palette", callback_data="palette")],
        [InlineKeyboardButton("💾 Save Palette", callback_data="save")],
        [InlineKeyboardButton("🔀 Color Schemes", callback_data="schemes")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_color_keyboard():
    keyboard = [
        [InlineKeyboardButton("🔄 New Color", callback_data="random")],
        [InlineKeyboardButton("💾 Save Color", callback_data="save_color")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== COMMAND HANDLERS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    
    # Initialize user session
    user_id = str(user.id)
    user_sessions[user_id] = {
        "saved_colors": [],
        "saved_palettes": []
    }
    
    welcome_message = (
        f"⚡ Welcome {user.first_name} to **ColorSparkBot**!\n\n"
        "Your creative color companion!\n\n"
        "**✨ Features:**\n"
        "• 🎨 Generate beautiful color palettes\n"
        "• 🎲 Get random colors instantly\n"
        "• 🔀 Explore color schemes\n"
        "• 💾 Save your favorite colors\n"
        "• 📋 Get HEX and RGB codes\n\n"
        "**🎯 Quick Start:**\n"
        "• Click 'Random Color' for instant inspiration\n"
        "• Click 'Generate Palette' for coordinated colors\n"
        "• Explore different color schemes\n\n"
        "⬇️ Let's spark some color inspiration!"
    )
    
    await update.message.reply_text(
        welcome_message,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = (
        "📖 **ColorSparkBot User Guide**\n\n"
        "**🎨 Generate Palette**\n"
        "• Creates a 5-color harmonious palette\n"
        "• Shows HEX and RGB codes\n\n"
        "**🎲 Random Color**\n"
        "• Generates a single random color\n"
        "• Shows HEX and RGB values\n\n"
        "**🔀 Color Schemes**\n"
        "• **Complementary:** Colors opposite on the color wheel\n"
        "• **Analogous:** Colors adjacent on the color wheel\n"
        "• **Triad:** Three evenly spaced colors\n"
        "• **Monochromatic:** Single hue variations\n\n"
        "**💾 Save Colors**\n"
        "• Save colors to your collection\n"
        "• View all your saved colors\n\n"
        "**Commands**\n"
        "/start - Start the bot\n"
        "/help - Show this help\n"
        "/random - Get a random color\n"
        "/palette - Generate a palette\n"
        "/saved - View saved colors"
    )
    
    await update.message.reply_text(
        help_text,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

async def random_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /random command"""
    r, g, b = generate_random_color()
    hex_code = rgb_to_hex(r, g, b)
    
    await update.message.reply_text(
        f"🎲 **Random Color**\n\n"
        f"⬛ {hex_code}\n\n"
        f"**HEX:** `{hex_code}`\n"
        f"**RGB:** `({r}, {g}, {b})`\n"
        f"**HSV:** `({int(colorsys.rgb_to_hsv(r/255, g/255, b/255)[0]*360)}, {int(colorsys.rgb_to_hsv(r/255, g/255, b/255)[1]*100)}%, {int(colorsys.rgb_to_hsv(r/255, g/255, b/255)[2]*100)}%)`\n\n"
        f"💡 Click 'New Color' for more inspiration!",
        parse_mode="Markdown",
        reply_markup=get_color_keyboard()
    )

async def palette_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /palette command"""
    base_color = generate_random_color()
    palette = generate_palette(base_color)
    
    color_text = "🎨 **Color Palette**\n\n"
    color_text += "**Harmonious Colors:**\n"
    
    for i, (r, g, b) in enumerate(palette, 1):
        hex_code = rgb_to_hex(r, g, b)
        color_text += f"{i}. {hex_code} (RGB: {r}, {g}, {b})\n"
    
    # Create a visual representation
    color_bar = ""
    for r, g, b in palette:
        hex_code = rgb_to_hex(r, g, b)
        color_bar += f"⬛{hex_code}⬛ "
    
    await update.message.reply_text(
        f"{color_text}\n\n{color_bar}\n\n💡 Click below to save or generate another!",
        parse_mode="Markdown",
        reply_markup=get_palette_keyboard()
    )

async def saved_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /saved command"""
    user_id = str(update.effective_user.id)
    saved = user_sessions.get(user_id, {}).get("saved_colors", [])
    
    if not saved:
        await update.message.reply_text(
            "📋 **No saved colors yet!**\n\n"
            "Generate a color and click 'Save Color' to add it here.",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        return
    
    saved_text = "📋 **Your Saved Colors**\n\n"
    for i, color in enumerate(saved[-10:], 1):
        r, g, b = color
        hex_code = rgb_to_hex(r, g, b)
        saved_text += f"{i}. {hex_code} (RGB: {r}, {g}, {b})\n"
    
    if len(saved) > 10:
        saved_text += f"\n... and {len(saved) - 10} more colors"
    
    await update.message.reply_text(
        saved_text,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

# ==================== CALLBACK HANDLERS ====================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button presses"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = str(update.effective_user.id)
    
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "saved_colors": [],
            "saved_palettes": []
        }
    
    if data == "palette":
        base_color = generate_random_color()
        palette = generate_palette(base_color)
        
        # Store current palette for saving
        user_sessions[user_id]["current_palette"] = palette
        
        color_text = "🎨 **Color Palette**\n\n"
        color_text += "**Harmonious Colors:**\n"
        
        for i, (r, g, b) in enumerate(palette, 1):
            hex_code = rgb_to_hex(r, g, b)
            color_text += f"{i}. {hex_code} (RGB: {r}, {g}, {b})\n"
        
        color_bar = ""
        for r, g, b in palette:
            hex_code = rgb_to_hex(r, g, b)
            color_bar += f"⬛{hex_code}⬛ "
        
        await query.edit_message_text(
            f"{color_text}\n\n{color_bar}\n\n💡 Click below to save or generate another!",
            parse_mode="Markdown",
            reply_markup=get_palette_keyboard()
        )
    
    elif data == "random":
        r, g, b = generate_random_color()
        hex_code = rgb_to_hex(r, g, b)
        
        # Store current color for saving
        user_sessions[user_id]["current_color"] = (r, g, b)
        
        await query.edit_message_text(
            f"🎲 **Random Color**\n\n"
            f"⬛ {hex_code}\n\n"
            f"**HEX:** `{hex_code}`\n"
            f"**RGB:** `({r}, {g}, {b})`\n\n"
            f"💡 Click 'New Color' for more inspiration!",
            parse_mode="Markdown",
            reply_markup=get_color_keyboard()
        )
    
    elif data == "save":
        palette = user_sessions.get(user_id, {}).get("current_palette", [])
        if palette:
            user_sessions[user_id]["saved_palettes"].append(palette)
            await query.edit_message_text(
                "✅ **Palette saved!**\n\n"
                f"You now have {len(user_sessions[user_id]['saved_palettes'])} saved palettes.",
                parse_mode="Markdown",
                reply_markup=get_palette_keyboard()
            )
        else:
            await query.edit_message_text(
                "❌ **No palette to save**\n\n"
                "Generate a palette first!",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
    
    elif data == "save_color":
        color = user_sessions.get(user_id, {}).get("current_color")
        if color:
            user_sessions[user_id]["saved_colors"].append(color)
            await query.edit_message_text(
                "✅ **Color saved!**\n\n"
                f"You now have {len(user_sessions[user_id]['saved_colors'])} saved colors.",
                parse_mode="Markdown",
                reply_markup=get_color_keyboard()
            )
        else:
            await query.edit_message_text(
                "❌ **No color to save**\n\n"
                "Generate a color first!",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
    
    elif data == "schemes":
        await query.edit_message_text(
            "🔀 **Color Schemes**\n\n"
            "Select a color scheme type to explore:",
            parse_mode="Markdown",
            reply_markup=get_scheme_keyboard()
        )
    
    elif data.startswith("scheme_"):
        scheme_type = data.replace("scheme_", "")
        base_color = generate_random_color()
        
        if scheme_type == "complementary":
            colors = [base_color, generate_complementary(base_color)]
            scheme_name = "Complementary"
        elif scheme_type == "analogous":
            colors = generate_analogous(base_color)
            scheme_name = "Analogous"
        elif scheme_type == "triad":
            colors = generate_triad(base_color)
            scheme_name = "Triad"
        elif scheme_type == "mono":
            colors = generate_monochromatic(base_color)
            scheme_name = "Monochromatic"
        elif scheme_type == "all":
            # Show all schemes
            schemes = {
                "Complementary": [base_color, generate_complementary(base_color)],
                "Analogous": generate_analogous(base_color),
                "Triad": generate_triad(base_color),
                "Monochromatic": generate_monochromatic(base_color)
            }
            
            result_text = "🎨 **All Color Schemes**\n\n"
            for scheme_name, scheme_colors in schemes.items():
                result_text += f"**{scheme_name}:**\n"
                for r, g, b in scheme_colors[:3]:
                    hex_code = rgb_to_hex(r, g, b)
                    result_text += f"• {hex_code}\n"
                result_text += "\n"
            
            await query.edit_message_text(
                f"{result_text}\n💡 Click below to explore each scheme!",
                parse_mode="Markdown",
                reply_markup=get_scheme_keyboard()
            )
            return
        else:
            colors = [base_color]
            scheme_name = "Unknown"
        
        color_text = f"🎨 **{scheme_name} Color Scheme**\n\n"
        color_text += "**Colors:**\n"
        
        for i, (r, g, b) in enumerate(colors, 1):
            hex_code = rgb_to_hex(r, g, b)
            color_text += f"{i}. {hex_code} (RGB: {r}, {g}, {b})\n"
        
        # Create color bar
        color_bar = ""
        for r, g, b in colors[:5]:
            hex_code = rgb_to_hex(r, g, b)
            color_bar += f"⬛{hex_code}⬛ "
        
        await query.edit_message_text(
            f"{color_text}\n\n{color_bar}\n\n💡 Try different schemes or generate a new palette!",
            parse_mode="Markdown",
            reply_markup=get_scheme_keyboard()
        )
    
    elif data == "saved":
        saved = user_sessions.get(user_id, {}).get("saved_colors", [])
        saved_palettes = user_sessions.get(user_id, {}).get("saved_palettes", [])
        
        if not saved and not saved_palettes:
            await query.edit_message_text(
                "📋 **No saved colors yet!**\n\n"
                "Generate a color and click 'Save Color' to add it here.",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
            return
        
        saved_text = "📋 **Your Saved Colors**\n\n"
        if saved:
            for i, color in enumerate(saved[-10:], 1):
                r, g, b = color
                hex_code = rgb_to_hex(r, g, b)
                saved_text += f"{i}. {hex_code} (RGB: {r}, {g}, {b})\n"
        
        if saved_palettes:
            saved_text += f"\n**Saved Palettes:** {len(saved_palettes)}\n"
        
        await query.edit_message_text(
            saved_text,
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
    
    elif data == "help":
        await help_command(update, context)
    
    elif data == "back":
        await query.edit_message_text(
            "🏠 **Main Menu**\n\n"
            "What color magic would you like to create?",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )

# ==================== MESSAGE HANDLERS ====================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    text = update.message.text.strip().lower()
    
    # Check if user entered a HEX color
    if text.startswith('#') and len(text) in [4, 7]:
        try:
            r, g, b = hex_to_rgb(text)
            await update.message.reply_text(
                f"🎨 **Color Information**\n\n"
                f"⬛ {text}\n\n"
                f"**HEX:** `{text}`\n"
                f"**RGB:** `({r}, {g}, {b})`\n\n"
                f"💡 Click below to generate more colors!",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
            return
        except:
            pass
    
    # Check for color name patterns (basic)
    color_names = {
        "red": (255, 0, 0),
        "green": (0, 255, 0),
        "blue": (0, 0, 255),
        "yellow": (255, 255, 0),
        "purple": (128, 0, 128),
        "orange": (255, 165, 0),
        "pink": (255, 192, 203),
        "brown": (165, 42, 42),
        "gray": (128, 128, 128),
        "black": (0, 0, 0),
        "white": (255, 255, 255)
    }
    
    if text in color_names:
        r, g, b = color_names[text]
        hex_code = rgb_to_hex(r, g, b)
        await update.message.reply_text(
            f"🎨 **Color Information**\n\n"
            f"⬛ {hex_code}\n\n"
            f"**Color:** {text.title()}\n"
            f"**HEX:** `{hex_code}`\n"
            f"**RGB:** `({r}, {g}, {b})`\n\n"
            f"💡 Click below for more colors!",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Default response
    await update.message.reply_text(
        "👋 **Send me a HEX code or color name!**\n\n"
        "Try typing:\n"
        "• A HEX code like `#FF5733`\n"
        "• A color name like `red` or `blue`\n\n"
        "Or use the buttons below for color inspiration!",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

# ==================== MAIN FUNCTION ====================
def main():
    """Start the bot"""
    print("⚡ Starting ColorSparkBot...")
    print("🎨 Ready to spark color inspiration!")
    
    # Build application
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .connect_timeout(30.0)
        .read_timeout(30.0)
        .build()
    )
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("random", random_command))
    application.add_handler(CommandHandler("palette", palette_command))
    application.add_handler(CommandHandler("saved", saved_command))
    
    # Add callback handler for buttons
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Add message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Start the bot
    print("✅ Bot is running! Press Ctrl+C to stop.")
    application.run_polling()

if __name__ == "__main__":
    main()
