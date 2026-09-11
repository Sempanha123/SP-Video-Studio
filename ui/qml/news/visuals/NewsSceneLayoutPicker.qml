import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"
AppCard {
    id: root
    property var controller
    ColumnLayout { anchors.fill: parent; spacing: Theme.spacing.sm
        SectionHeader { title: "Scene Layout"; subtitle: "Responsive presets resolve to normalized SceneOverlay geometry." }
        AppComboBox { id: picker; Layout.fillWidth: true; model: root.controller ? root.controller.layouts : []; textRole: "name"; valueRole: "id" }
        RowLayout { Layout.fillWidth: true
            AppButton { text: "Apply Layout"; compact: true; enabled: picker.currentValue!==undefined; onClicked: if(root.controller) root.controller.applyLayout(String(picker.currentValue||"headline_focus"),"replace") }
            SecondaryButton { text: "Missing Only"; compact: true; onClicked: if(root.controller) root.controller.applyLayout(String(picker.currentValue||"headline_focus"),"missing") }
            SecondaryButton { text: "Detach"; compact: true; onClicked: if(root.controller) root.controller.detachLayout() }
        }
        Text { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: root.controller && root.controller.currentVisual.layout.customized ? "Customized • reapplying a layout can replace only News-managed elements." : "Layout stays linked until detached or substantially edited."; color: Theme.colors.textMuted; font.pixelSize: Theme.type.caption }
    }
}
