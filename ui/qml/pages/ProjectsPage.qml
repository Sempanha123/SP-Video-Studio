import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

Item {
    id: root
    signal navigateRequested(string page, string workflow)
    ColumnLayout {
        anchors.fill: parent; spacing: Theme.spacing.xl
        RowLayout { Layout.fillWidth: true
            ColumnLayout { Layout.fillWidth: true; spacing: 2
                Text { text: "Projects"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.titleLarge; font.weight: Theme.type.semibold }
                Text { text: "Keep your video work organized in one place."; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.body }
            }
            AppButton { text: "New Project"; iconName: "plus"; onClicked: root.navigateRequested("create", "news") }
        }
        AppCard { Layout.fillWidth: true; Layout.fillHeight: true; EmptyState { anchors.centerIn: parent; title: "No projects yet"; description: "Your projects will appear here after you create your first video."; iconName: "projects"; actionText: "Create Project"; onActionClicked: root.navigateRequested("create", "news") } }
    }
}
