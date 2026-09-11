import QtQuick 2.15
import QtQuick.Controls 2.15
import "../theme"

Dialog {
    id: control
    modal: true
    padding: Theme.spacing.xl
    background: Rectangle {
        radius: Theme.radius.large
        color: Theme.colors.surfaceRaised
        border.color: Theme.colors.border
        border.width: 1
    }
}
