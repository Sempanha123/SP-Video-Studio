import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Phase25 1.0
import "../theme"
import "../components"
Item {
    id: root
    signal toastRequested(string message,string variant)
    AssetImportDialog { id: importDialog }
    AssetRelinkDialog { id: relinkDialog }
    ColumnLayout { anchors.fill: parent; spacing: Theme.spacing.md
        PageHeader { Layout.fillWidth: true; title: "Assets"; description: "Reusable media for every project. Drag into the Timeline or add it from a project.";
            actions: [
                AppButton { text: "Refresh"; variant: "quiet"; iconName: "refresh"; onClicked: AssetLibrary.refresh() },
                AppButton { text: "Import"; iconName: "plus"; onClicked: importDialog.open() }
            ]
        }
        AssetFilterBar { Layout.fillWidth: true; onQueryChanged: function(v){AssetLibrary.setQuery(v)}; onFilterChanged: function(v){AssetLibrary.setFilter(v)}; onSortChanged: function(v){AssetLibrary.setSort(v)} }
        SplitView { Layout.fillWidth: true; Layout.fillHeight: true
            AssetCollectionSidebar { SplitView.preferredWidth: 184; SplitView.minimumWidth: 150; collections: AssetLibrary.collections; onCollectionSelected: function(id){AssetLibrary.setCollection(id)} }
            AssetGrid { SplitView.fillWidth: true; SplitView.fillHeight: true; SplitView.minimumWidth: 420; assets: AssetLibrary.assets; onSelected: function(id){AssetLibrary.selectAsset(id)} }
            AppCard { elevated: true; SplitView.preferredWidth: 292; SplitView.minimumWidth: 250; SplitView.maximumWidth: 380; SplitView.fillHeight: true; AssetInspector { anchors.fill: parent; anchors.margins: Theme.spacing.lg; asset: AssetLibrary.selectedAsset } }
        }
    }
    Connections { target: AssetLibrary; function onOperationSucceeded(message){root.toastRequested(message,"success")} function onOperationFailed(message){root.toastRequested(message,"error")} }
}
