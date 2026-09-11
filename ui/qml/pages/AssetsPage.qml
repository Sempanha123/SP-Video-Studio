import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

Item {
    id: root
    signal toastRequested(string message, string variant)
    property int selectedTab: 0
    ColumnLayout { anchors.fill: parent; spacing: Theme.spacing.lg
        RowLayout { Layout.fillWidth: true
            ColumnLayout { Layout.fillWidth: true; spacing: 2
                Text { text: "Asset Library"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.titleLarge; font.weight: Theme.type.semibold }
                Text { text: "Media, audio, images and project assets will live here."; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.body }
            }
            AppButton { text: "Import"; iconName: "plus"; onClicked: root.toastRequested("Media importing will be available in a later phase.", "info") }
        }
        RowLayout { spacing: Theme.spacing.xs
            Repeater { model: ["All", "Video", "Images", "Audio"]
                delegate: AppButton { required property string modelData; required property int index; text: modelData; compact: true; variant: root.selectedTab === index ? "secondary" : "ghost"; onClicked: root.selectedTab = index }
            }
        }
        AppCard { Layout.fillWidth: true; Layout.fillHeight: true; EmptyState { anchors.centerIn: parent; title: "Your media library is empty"; description: "Imported media will be organized here without modifying your originals."; iconName: "assets" } }
    }
}
