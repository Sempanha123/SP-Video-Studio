import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Window 2.15
import SPVideoStudio.Commands 1.0
import "../theme"
Dialog {
    id: control
    property var previousFocusItem: null
    property var initialFocusItem: null
    modal: true
    focus: true
    padding: Theme.spacing.xlg
    dim: true
    Accessible.name: title && title.length > 0 ? title : "Dialog"
    Accessible.role: Accessible.Dialog
    onAboutToShow: {
        var w = control.Window.window
        previousFocusItem = w ? w.activeFocusItem : null
    }
    onOpened: {
        Commands.setModalOpen(true)
        if (initialFocusItem && initialFocusItem.forceActiveFocus) initialFocusItem.forceActiveFocus(Qt.TabFocusReason)
        else if (contentItem && contentItem.forceActiveFocus) contentItem.forceActiveFocus(Qt.TabFocusReason)
    }
    onClosed: {
        Commands.setModalOpen(false)
        if (previousFocusItem && previousFocusItem.forceActiveFocus) previousFocusItem.forceActiveFocus(Qt.TabFocusReason)
        previousFocusItem = null
    }
    background: Rectangle { radius: Theme.radius.dialog; color: Theme.colors.surfaceRaised; border.color: Theme.colors.border; border.width: 1 }
    Overlay.modal: Rectangle { color: Theme.colors.overlayScrim }
}
