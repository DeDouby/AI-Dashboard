###############################################################################
# UNIFIED SLIDER - Supports both single-point and range (2-point) modes
# Created for consistent scaling across all overlays (Light, Exhaust, Circulation)
#
# USAGE:
#   - Single point: UnifiedSlider(min=0, max=100, mode='single')
#   - Range (2-point): UnifiedSlider(min=0, max=100, mode='range')
#
# Benefits:
#   - All size parameters use dp_scaled() for cross-platform consistency
#   - Easy to switch between 1-point and 2-point sliders
#   - Unified look and feel across all overlays
#   - Future-proof for light_overlay 2-point expansion
###############################################################################

from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, StringProperty, BooleanProperty, AliasProperty
from kivy.graphics import Color, RoundedRectangle, Ellipse, Line
from kivy.core.window import Window
from dashboard_gui.ui.scaling_utils import dp_scaled


class UnifiedSlider(Widget):
    """
    A flexible slider that supports both single-point and range (2-point) modes.
    
    Properties:
        - min: minimum value (range mode: left handle)
        - max: maximum value (range mode: right handle, single: current value)
        - range_min: minimum allowed value
        - range_max: maximum allowed value
        - mode: 'single' or 'range'
        - value: alias for max_value in single mode (for compatibility with Kivy Slider)
    """
    
    min_value = NumericProperty(0)
    max_value = NumericProperty(100)
    range_min = NumericProperty(0)
    range_max = NumericProperty(100)
    mode = StringProperty('single')  # 'single' or 'range'
    fill_entire_track = BooleanProperty(False)  # If True, fill entire track (for light slider)

    def _get_value(self):
        """In single mode, value is max_value. In range mode, it's... well, undefined (we use min/max)"""
        return self.max_value if self.mode == 'single' else self.max_value

    def _set_value(self, value):
        """Setting value in single mode updates max_value"""
        if self.mode == 'single':
            self.max_value = value
        else:
            self.max_value = value

    # Create an alias property 'value' that maps to max_value for compatibility
    value = AliasProperty(_get_value, _set_value, bind=('max_value',))

    def __init__(self, min=0, max=100, range_min=0, range_max=100, mode='single', fill_entire_track=False, **kwargs):
        super().__init__(**kwargs)
        self.range_min = range_min
        self.range_max = range_max
        self.min_value = min
        self.max_value = max
        self.mode = mode
        self.fill_entire_track = fill_entire_track
        
        self.bind(
            pos=self._update_canvas, 
            size=self._update_canvas, 
            min_value=self._update_canvas, 
            max_value=self._update_canvas,
            mode=self._update_canvas,
            fill_entire_track=self._update_canvas
        )

    def _update_canvas(self, *args):
        self.canvas.after.clear()
        
        # Size parameters - ALL using dp_scaled for cross-platform consistency
        track_h = dp_scaled(10)
        active_h = dp_scaled(14)
        handle_size = dp_scaled(34)
        
        with self.canvas.after:
            # =====================
            # 1. BACK TRACK
            # =====================
            Color(0.15, 0.15, 0.15, 1)
            RoundedRectangle(
                pos=(self.x, self.center_y - track_h / 2),
                size=(self.width, track_h),
                radius=[dp_scaled(6)]
            )
            
            if self.mode == 'single':
                self._draw_single_mode(handle_size, active_h, track_h)
            else:  # 'range'
                self._draw_range_mode(handle_size, active_h, track_h)

    def _draw_single_mode(self, handle_size, active_h, track_h):
        """Draw single-point slider (like standard Slider)"""
        Color(0, 1, 0, 0.75)
        
        # Guard gegen Division by Zero
        range_span = self.range_max - self.range_min
        if range_span <= 0:
            range_span = 1
        
        # Position of the handle
        x_val = self.x + ((self.max_value - self.range_min) / range_span) * self.width
        
        # Active track from left to current value
        RoundedRectangle(
            pos=(self.x, self.center_y - active_h / 2),
            size=(x_val - self.x, active_h),
            radius=[dp_scaled(8)]
        )
        
        # Single handle
        Color(1, 1, 1, 1)
        Ellipse(
            pos=(x_val - handle_size / 2, self.center_y - handle_size / 2),
            size=(handle_size, handle_size)
        )

    def _draw_range_mode(self, handle_size, active_h, track_h):
        """Draw range-slider (2-point slider)"""
        Color(0, 1, 0, 0.75)
        
        # Guard gegen Division by Zero
        range_span = self.range_max - self.range_min
        if range_span <= 0:
            range_span = 1
        
        # Positions of both handles
        x_min = self.x + ((self.min_value - self.range_min) / range_span) * self.width
        x_max = self.x + ((self.max_value - self.range_min) / range_span) * self.width
        
        if self.fill_entire_track:
            # FULL TRACK grün gefüllt (für Light-Slider)
            RoundedRectangle(
                pos=(self.x, self.center_y - active_h / 2),
                size=(self.width, active_h),
                radius=[dp_scaled(8)]
            )
        else:
            # Active range between handles
            RoundedRectangle(
                pos=(x_min, self.center_y - active_h / 2),
                size=(x_max - x_min, active_h),
                radius=[dp_scaled(8)]
            )
        
        # Left and right handles
        Color(1, 1, 1, 1)
        
        Ellipse(
            pos=(x_min - handle_size / 2, self.center_y - handle_size / 2),
            size=(handle_size, handle_size)
        )
        
        Ellipse(
            pos=(x_max - handle_size / 2, self.center_y - handle_size / 2),
            size=(handle_size, handle_size)
        )

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._handle_touch(touch)
            return True

    def on_touch_move(self, touch):
        if self.collide_point(*touch.pos):
            self._handle_touch(touch)
            return True

    def _handle_touch(self, touch):
        """Handle touch events for both single and range modes"""
        # Guard gegen Division by Zero
        range_span = self.range_max - self.range_min
        if range_span <= 0:
            return  # Kein Touch-Handling wenn Range ungültig
        
        # Relative position (0–1 clamped)
        if self.width <= 0:
            return  # Guard gegen Division durch Null bei width
        
        relative_x = (touch.x - self.x) / self.width
        relative_x = max(0.0, min(1.0, relative_x))
        
        # Scale to range value
        raw_val = relative_x * range_span + self.range_min
        val = int(round(raw_val))
        
        if self.mode == 'single':
            self._handle_single_touch(val, relative_x)
        else:  # 'range'
            self._handle_range_touch(val, relative_x)

    def _handle_single_touch(self, val, relative_x):
        """Handle touch for single-point mode"""
        # HARD SNAP TO MIN
        if relative_x < 0.03:
            self.max_value = self.range_min
            return
        
        # Clamp to range
        val = max(self.range_min, min(self.range_max, val))
        self.max_value = val

    def _handle_range_touch(self, val, relative_x):
        """Handle touch for range (2-point) mode"""
        # HARD SNAP TO ZERO
        if relative_x < 0.03:
            self.min_value = self.range_min
            self.max_value = self.range_min
            return
        
        # Normal range limiting
        val = max(self.range_min, min(self.range_max, val))
        
        # Handle logic: which handle is closer?
        dist_min = abs(val - self.min_value)
        dist_max = abs(val - self.max_value)
        
        # Special case: if both at 0 and we drag right
        if self.min_value == self.range_min and self.max_value == self.range_min:
            self.max_value = val
            return

        if dist_min < dist_max:
            # Move left handle, but not over right
            self.min_value = min(val, self.max_value)
        else:
            # Move right handle, but not under left
            self.max_value = max(val, self.min_value)
