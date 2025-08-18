export function jsTheme(player) {
    const controlBar = player.controlBar.el();

    // Create top and bottom rows
    const topRow = document.createElement('div');
    topRow.className = 'top-row';    
    const bottomRow = document.createElement('div');
    bottomRow.className = 'bottom-row';

    // Create groups inside top row
    const topLeft = document.createElement('div');
    topLeft.className = 'left-group';
    const topRight = document.createElement('div');
    topRight.className = 'right-group';


    // Bottom row groups
    const bottomLeftTime = player.controlBar.currentTimeDisplay.el();
    bottomLeftTime.classList.add('time-current');
    const bottomRightTime = player.controlBar.durationDisplay.el();
    bottomRightTime.classList.add('time-duration');

    const bottomProgress = player.controlBar.progressControl.el();

    // Remove all children from controlBar first
    while (controlBar.firstChild) {
        controlBar.removeChild(controlBar.firstChild);
    }

    // Add playButton and volumePanel to top left
    topLeft.appendChild(player.controlBar.playToggle.el());
    topLeft.appendChild(player.controlBar.volumePanel.el());

    // Add fullscreen & captions to top right
    const captionsBtn = player.controlBar.subsCapsButton.el();
    captionsBtn.classList.add('captions-btn');
    topRight.appendChild(captionsBtn);
    topRight.appendChild(player.controlBar.fullscreenToggle.el());

    // Add groups to top row
    topRow.appendChild(topLeft);
    topRow.appendChild(topRight);

    // Add current time, progress bar, duration to bottom row
    bottomRow.appendChild(bottomLeftTime);
    bottomRow.appendChild(bottomProgress);
    bottomRow.appendChild(bottomRightTime);

    // Append rows to controlBar
    controlBar.appendChild(topRow);
    controlBar.appendChild(bottomRow);
}
