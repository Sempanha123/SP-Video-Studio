import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

RowLayout {
    id: root
    property var controller: null
    signal setupRequested()
    signal exportRequested(bool bilingual)
    signal approveRequested()
    spacing: Theme.spacing.sm

    AppTextField { Layout.preferredWidth: 230; placeholderText: "Search source or translation"; onTextChanged: if (root.controller) root.controller.setSearch(text) }
    AppComboBox {
        Layout.preferredWidth: 150
        model: ["All", "Unreviewed", "Reviewed", "Edited", "Needs Attention", "Locked"]
        onActivated: {
            var values = ["all", "unreviewed", "reviewed", "edited", "needs_attention", "locked"]
            if (root.controller) root.controller.setFilter(values[currentIndex])
        }
    }
    Item { Layout.fillWidth: true }
    SecondaryButton { text: "Sync Source"; compact: true; enabled: root.controller && !root.controller.busy; onClicked: root.controller.syncSource() }
    SecondaryButton { text: "Copy"; compact: true; enabled: root.controller; onClicked: root.controller.copyTranslation() }
    SecondaryButton { text: "Export"; compact: true; enabled: root.controller; onClicked: root.exportRequested(false) }
    SecondaryButton { text: "Bilingual"; compact: true; enabled: root.controller; onClicked: root.exportRequested(true) }
    AppButton { text: "Approve"; compact: true; enabled: root.controller && !root.controller.busy; onClicked: root.approveRequested() }
    SecondaryButton { text: "New"; compact: true; onClicked: root.setupRequested() }
}
