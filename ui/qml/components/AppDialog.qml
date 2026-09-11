import QtQuick 2.15
import QtQuick.Controls 2.15
import "../theme"
Dialog {
    id: control
    modal: true
    padding: Theme.spacing.xlg
    dim: true
    background: Rectangle { radius: Theme.radius.dialog; color: Theme.colors.surfaceRaised; border.color: Theme.colors.border; border.width: 1 }
    Overlay.modal: Rectangle { color: Theme.colors.overlayScrim }
}
