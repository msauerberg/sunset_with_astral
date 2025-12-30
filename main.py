import numpy as np
from datetime import datetime, timedelta
from astral import LocationInfo
from astral.sun import sun
import pandas as pd
import matplotlib.pyplot as plt
import pytz

def get_sunset_hours(city: str,
                     region: str,
                     timezone: str,
                     latitude: float,
                     longitude: float,
                     year: int):
    """
    Calculate sunset times for every day of the year.
    
    Parameters:
    -----------
    city : str
        City name, e.g., Hamburg
    region : str
        Region/country name, e.g., Germany
    timezone : str
        Timezone string (e.g., 'Europe/Berlin')
    latitude : float
        Latitude in decimal degrees (positive = North)
    longitude : float
        Longitude in decimal degrees (positive = East)
    year : int
        Year to calculate sunset times for
        
    Returns:
    --------
    pd.DataFrame with columns: year, city, dates, sunset_time, sunset_time_utc, sunset_hours
    """
    # Create location object
    city_data = LocationInfo(city, region, timezone, latitude, longitude)

    # Use UTC for astronomical calculations
    utc = pytz.UTC

    start_date = datetime(year, 1, 1)
    end_date = datetime(year, 12, 31)

    dates = []
    sunset_times = []
    sunset_times_utc = []
    sunset_hours = []

    current_date = start_date

    while current_date <= end_date:
        # sunset times from astral
        s_utc = sun(city_data.observer, date=current_date, tzinfo=utc)
        s_local = sun(city_data.observer, date=current_date, tzinfo=city_data.timezone)

        # Store datetimes
        dates.append(current_date.replace(tzinfo=None))
        sunset_times_utc.append(s_utc["sunset"].replace(tzinfo=None))
        sunset_times.append(s_local["sunset"].replace(tzinfo=None))
        
        # Convert to decimal hours (UTC)
        st = s_utc["sunset"]
        decimal_hour = st.hour + st.minute / 60 + st.second / 3600
        sunset_hours.append(decimal_hour)

        current_date += timedelta(days=1)

    return pd.DataFrame({
        "year": year,
        "city": city,
        "dates": dates,
        "sunset_time": sunset_times,
        "sunset_time_utc": sunset_times_utc,
        "sunset_hours": sunset_hours
    })


def get_derivative(sunset_hours: list):
    """
    Calculate the first derivative (rate of change) of sunset times.
    
    Parameters:
    -----------
    sunset_hours : list or array
        List of sunset times in decimal hours (e.g., [15.18, 15.20, ...])
        
    Returns:
    --------
    list of float
        Rate of change in minutes per day
    """
    derivatives = []

    for i in range(len(sunset_hours)):
        if i == 0:
            # Forward difference
            deriv = (sunset_hours[i+1] - sunset_hours[i]) * 60
        elif i == len(sunset_hours) - 1:
            # Backward difference
            deriv = (sunset_hours[i] - sunset_hours[i-1]) * 60
        else:
            # Central difference
            deriv = (sunset_hours[i+1] - sunset_hours[i-1]) / 2 * 60
        
        derivatives.append(deriv)

    return derivatives


def plot_sunset_analysis(sunset_data: pd.DataFrame, derivatives: list, 
                         dst_spring_date=None, dst_fall_date=None):
    """
    Create visualization of sunset times and rate of change.
    
    Parameters:
    -----------
    sunset_data : pd.DataFrame
        DataFrame from get_sunset_hours() function
    derivatives : list
        List from get_derivative() function
    dst_spring_date : datetime, optional
        Date when DST starts (spring forward)
    dst_fall_date : datetime, optional
        Date when DST ends (fall back)
    """
    dates = pd.to_datetime(sunset_data["dates"])
    sunset_hours = sunset_data["sunset_hours"].values
    year = int(sunset_data["year"].unique().item())
    
    # Create figure with two subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

    # Plot 1: Sunset times throughout the year
    ax1.plot(dates, sunset_hours, linewidth=2, color='darkorange')
    ax1.set_xlabel('Date', fontsize=12)
    ax1.set_ylabel('Sunset Time UTC (hours)', fontsize=12)
    ax1.set_title(f'Sunset Times in {sunset_data["city"].iloc[0]} Throughout {year} (UTC, no DST)', 
                  fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)

    # Add DST transition markers if provided
    if dst_spring_date is not None:
        ax1.axvline(x=dst_spring_date, color='green', linestyle=':', linewidth=2, alpha=0.6)
        ax1.text(dst_spring_date, max(sunset_hours) - 0.3, 
                 f'DST Start\n({dst_spring_date.strftime("%b %d")})', 
                 ha='center', fontsize=9, 
                 bbox=dict(boxstyle='round,pad=0.4', fc='lightgreen', alpha=0.7))

    if dst_fall_date is not None:
        ax1.axvline(x=dst_fall_date, color='brown', linestyle=':', linewidth=2, alpha=0.6)
        ax1.text(dst_fall_date, max(sunset_hours) - 0.3, 
                 f'DST End\n({dst_fall_date.strftime("%b %d")})', 
                 ha='center', fontsize=9, 
                 bbox=dict(boxstyle='round,pad=0.4', fc='wheat', alpha=0.7))

    # Format y-axis to show times
    y_min = int(min(sunset_hours)) - 1
    y_max = int(max(sunset_hours)) + 2
    y_ticks = range(y_min, y_max)
    y_labels = [f"{h}:00" for h in y_ticks]
    ax1.set_yticks(y_ticks)
    ax1.set_yticklabels(y_labels)

    # Plot 2: first derivative
    ax2.plot(dates, derivatives, linewidth=2, color='steelblue')
    ax2.axhline(y=0, color='red', linestyle='--', linewidth=1, alpha=0.5)
    ax2.set_xlabel('Date', fontsize=12)
    ax2.set_ylabel('Rate of Change (minutes/day)', fontsize=12)
    ax2.set_title(f'Rate of Change in Sunset Time Throughout {year}', 
                  fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)

    # Find turning points - where derivative crosses zero
    # Summer solstice: derivative changes from positive to negative
    summer_turning_point_idx = None
    for i in range(1, len(derivatives)):
        if derivatives[i-1] > 0 and derivatives[i] <= 0:
            summer_turning_point_idx = i
            break
    
    # If not found with strict condition, find where it's closest to zero after being positive
    if summer_turning_point_idx is None:
        positive_to_negative = [i for i in range(1, len(derivatives)) 
                                if derivatives[i-1] > 0 and derivatives[i] < derivatives[i-1]]
        if positive_to_negative:
            # Find the point closest to zero
            candidates = [i for i in positive_to_negative if derivatives[i] < 0.5]
            if candidates:
                summer_turning_point_idx = min(candidates, key=lambda i: abs(derivatives[i]))

    # Winter solstice: derivative changes from negative to positive
    winter_turning_point_idx = None
    for i in range(1, len(derivatives)):
        if derivatives[i-1] < 0 and derivatives[i] >= 0:
            winter_turning_point_idx = i
            break
    
    # If not found with strict condition, find where it's closest to zero after being negative
    if winter_turning_point_idx is None:
        negative_to_positive = [i for i in range(1, len(derivatives)) 
                                if derivatives[i-1] < 0 and derivatives[i] > derivatives[i-1]]
        if negative_to_positive:
            # Find the point closest to zero
            candidates = [i for i in negative_to_positive if derivatives[i] > -0.5]
            if candidates:
                winter_turning_point_idx = min(candidates, key=lambda i: abs(derivatives[i]))

    # Add annotations for maximum changes
    max_increase_idx = np.argmax(derivatives)
    max_decrease_idx = np.argmin(derivatives)

    ax2.annotate(f'Max increase\n{derivatives[max_increase_idx]:.2f} min/day\n{dates.iloc[max_increase_idx].strftime("%b %d")}',
                 xy=(dates.iloc[max_increase_idx], derivatives[max_increase_idx]),
                 xytext=(10, 20), textcoords='offset points',
                 bbox=dict(boxstyle='round,pad=0.5', fc='lightgreen', alpha=0.7),
                 arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))

    ax2.annotate(f'Max decrease\n{derivatives[max_decrease_idx]:.2f} min/day\n{dates.iloc[max_decrease_idx].strftime("%b %d")}',
                 xy=(dates.iloc[max_decrease_idx], derivatives[max_decrease_idx]),
                 xytext=(10, -30), textcoords='offset points',
                 bbox=dict(boxstyle='round,pad=0.5', fc='lightcoral', alpha=0.7),
                 arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))

    # Add annotation for turning points
    if summer_turning_point_idx is not None:
        ax2.axvline(x=dates.iloc[summer_turning_point_idx], color='purple', linestyle='--', linewidth=2, alpha=0.6)
        ax2.annotate(f'Summer Solstice\n{dates.iloc[summer_turning_point_idx].strftime("%b %d")}\n(Longer → Shorter)',
                     xy=(dates.iloc[summer_turning_point_idx], 0),
                     xytext=(20, 40), textcoords='offset points',
                     bbox=dict(boxstyle='round,pad=0.5', fc='lavender', alpha=0.8),
                     arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0', color='purple'))

    if winter_turning_point_idx is not None:
        ax2.axvline(x=dates.iloc[winter_turning_point_idx], color='darkblue', linestyle='--', linewidth=2, alpha=0.6)
        ax2.annotate(f'Winter Solstice\n{dates.iloc[winter_turning_point_idx].strftime("%b %d")}\n(Shorter → Longer)',
                     xy=(dates.iloc[winter_turning_point_idx], 0),
                     xytext=(-80, -40), textcoords='offset points',
                     bbox=dict(boxstyle='round,pad=0.5', fc='lightblue', alpha=0.8),
                     arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0', color='darkblue'))

    plt.tight_layout()
    plt.show()

    # Print statistics
    sunset_times = sunset_data["sunset_time"]
    sunset_times_utc = sunset_data["sunset_time_utc"]
    earliest_idx = np.argmin(sunset_hours)
    latest_idx = np.argmax(sunset_hours)
    
    print(f"=== Sunset Time Statistics for {sunset_data['city'].iloc[0]} {year} ===\n")
    print(f"Earliest sunset: {sunset_times.iloc[earliest_idx].strftime('%H:%M')} (local) / {sunset_times_utc.iloc[earliest_idx].strftime('%H:%M UTC')} on {dates.iloc[earliest_idx].strftime('%B %d')}")
    print(f"Latest sunset: {sunset_times.iloc[latest_idx].strftime('%H:%M')} (local) / {sunset_times_utc.iloc[latest_idx].strftime('%H:%M UTC')} on {dates.iloc[latest_idx].strftime('%B %d')}")
    print(f"\nMaximum rate of increase: {max(derivatives):.2f} minutes/day on {dates.iloc[max_increase_idx].strftime('%B %d')}")
    print(f"Maximum rate of decrease: {min(derivatives):.2f} minutes/day on {dates.iloc[max_decrease_idx].strftime('%B %d')}")
    
    if winter_turning_point_idx is not None:
        print(f"\n*** Winter Solstice (shorter → longer days): {dates.iloc[winter_turning_point_idx].strftime('%B %d, %Y')} ***")
        print(f"    This is the shortest day of the year")
    
    if summer_turning_point_idx is not None:
        print(f"\n*** Summer Solstice (longer → shorter days): {dates.iloc[summer_turning_point_idx].strftime('%B %d, %Y')} ***")
        print(f"    This is the longest day of the year")